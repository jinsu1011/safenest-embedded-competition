/*
 * SafeNest ESP32 sensor node
 *
 * Sensors:
 *   - Seeed MR60BHA2 (UART): respiration and heart rate
 *   - Sensirion SCD40/SCD4x (I2C): CO2
 *   - PIR (digital input): motion
 *   - Waveshare Thermal Camera HAT / MI48xx (I2C control + SPI data): 80 x 62
 *
 * Transport:
 *   - TCP for low-rate mmWave/CO2/PIR JSON telemetry
 *   - Chunked UDP for big-endian uint16 Thermal frames
 *
 * The Arduino loop never calls delay(). Sensor scheduling uses millis().
 * TCP reconnect/writes and Thermal UDP writes run in separate FreeRTOS tasks.
 * If the network is slow, the one-slot thermal queue keeps only the newest frame.
 */

#include <Arduino.h>
#include <esp_system.h>
#include <freertos/event_groups.h>
#include <freertos/semphr.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <SPI.h>
#include <SensirionI2cScd4x.h>
#include "Seeed_Arduino_mmWave.h"
#include "secrets.h"

// -----------------------------------------------------------------------------
// Device identity. Wi-Fi and Raspberry Pi settings live in ignored secrets.h.
// ----------------------------------------------------------------------------
constexpr char DEVICE_ID[] = "esp32-01";
char bootId[33] = {};
constexpr uint16_t THERMAL_UDP_PORT = 5005;

// -----------------------------------------------------------------------------
// ESP32 Dev Module wiring (matches the existing standalone sensor tests).
// ----------------------------------------------------------------------------
constexpr int PIN_I2C_SDA = 21;
constexpr int PIN_I2C_SCL = 22;
constexpr int PIN_PIR = 13;
constexpr int PIN_MMWAVE_RX = 16;  // ESP32 RX <- MR60BHA2 TX
constexpr int PIN_MMWAVE_TX = 17;  // ESP32 TX -> MR60BHA2 RX

constexpr int PIN_THERMAL_SCLK = 18;
constexpr int PIN_THERMAL_MISO = 19;
constexpr int PIN_THERMAL_MOSI = 23;
constexpr int PIN_THERMAL_CS = 27;
constexpr int PIN_THERMAL_READY = 26;
constexpr int PIN_THERMAL_RESET = 25;

constexpr uint32_t USB_BAUD = 115200;
constexpr uint32_t MMWAVE_BAUD = 115200;
constexpr uint32_t THERMAL_SPI_HZ = 8000000;

// Runtime schedules. SCD4x periodic mode creates a new sample about every 5 s.
constexpr uint32_t PIR_PERIOD_MS = 20;
constexpr uint32_t CO2_POLL_PERIOD_MS = 500;
constexpr uint32_t CO2_RETRY_PERIOD_MS = 3000;
constexpr uint32_t CO2_STOP_WAIT_MS = 1000;
constexpr uint32_t CO2_MAX_CONSECUTIVE_FAILURES = 3;
// One scalar snapshot per second is sufficient for the default LCD display.
// TCP writes remain isolated in their own task.
constexpr uint32_t TELEMETRY_PERIOD_MS = 1000;
constexpr uint32_t HEALTH_LOG_PERIOD_MS = 10000;
constexpr uint32_t MMWAVE_STALE_MS = 10000;
constexpr uint32_t CO2_STALE_MS = 15000;
// The MR60 reports 0x0F09 occupancy on its own cadence, independent of the
// respiration/heart-rate stream. This bound only has to outlive normal report
// gaps; once it lapses the field goes null (unknown), which suppresses mmWave
// inference rather than asserting an empty room.
constexpr uint32_t PRESENCE_MAX_AGE_MS = 5000;
constexpr char NODE_FIRMWARE_VERSION[] =
    "safenest-esp32-sensor-node/1.4.0-tcp-priority.1";
constexpr char DIAGNOSTIC_BUILD_ID[] = "tcp-priority-20260831-01";

enum class Co2State : uint8_t {
  RETRY_WAIT,
  STOP_WAIT,
  RUNNING,
};

// -----------------------------------------------------------------------------
// Thermal-camera constants (MI48xx + MI0801/MI0802, 80 x 62).
// ----------------------------------------------------------------------------
constexpr uint8_t THERMAL_ADDRESS_A = 0x40;
constexpr uint8_t THERMAL_ADDRESS_B = 0x41;
constexpr uint8_t SCD4X_ADDRESS = 0x62;

constexpr uint8_t REG_EVK_TEST = 0x00;
constexpr uint8_t REG_SENSOR_POWERUP = 0xB0;
constexpr uint8_t REG_FRAME_MODE = 0xB1;
constexpr uint8_t REG_FW_VERSION_1 = 0xB2;
constexpr uint8_t REG_FW_VERSION_2 = 0xB3;
constexpr uint8_t REG_FRAME_RATE = 0xB4;
constexpr uint8_t REG_STATUS = 0xB6;
constexpr uint8_t REG_SENSOR_TYPE = 0xBA;

constexpr uint8_t STATUS_DATA_READY = 0x10;
constexpr uint8_t STATUS_BOOTING = 0x20;
constexpr uint8_t MODE_CONTINUOUS = 0x02;

constexpr size_t THERMAL_WIDTH = 80;
constexpr size_t THERMAL_HEIGHT = 62;
constexpr size_t THERMAL_PIXEL_COUNT = THERMAL_WIDTH * THERMAL_HEIGHT;
constexpr size_t THERMAL_HEADER_WORDS = THERMAL_WIDTH;
constexpr size_t THERMAL_CAPTURE_WORDS =
    THERMAL_HEADER_WORDS + THERMAL_PIXEL_COUNT;

// Set divisor 4: for a 25 FPS sensor this requests about 6.25 FPS.
// Lowering this value raises bandwidth and ESP32 CPU/SPI load.
constexpr uint8_t THERMAL_FRAME_RATE_DIVIDER = 4;

// -----------------------------------------------------------------------------
// SafeNest TCP protocol v1 for scalar telemetry.
// Outer header (16 bytes, network byte order):
//   magic[4]="SNST", version:u8, type:u8, flags:u16,
//   packet_sequence:u32, payload_length:u32
// Packet type 1 payload: UTF-8 JSON.
// Thermal UDP logical payload: 16-byte metadata followed by 4960 uint16 words.
// -----------------------------------------------------------------------------
constexpr uint8_t PROTOCOL_VERSION = 1;
constexpr uint8_t PACKET_TELEMETRY_JSON = 1;
constexpr uint8_t PACKET_THERMAL_U16_BE = 2;
constexpr size_t PACKET_HEADER_SIZE = 16;
constexpr size_t THERMAL_META_SIZE = 16;

// SafeNest Thermal UDP v1. A 1200-byte datagram stays below the common
// Ethernet/Wi-Fi MTU after IPv4 and UDP headers, avoiding IP fragmentation.
// Header fields are network byte order and every chunk repeats the frame CRC32.
constexpr char THERMAL_UDP_MAGIC[] = "SNTU";
constexpr uint8_t THERMAL_UDP_VERSION = 1;
constexpr size_t THERMAL_UDP_HEADER_SIZE = 32;
constexpr size_t THERMAL_UDP_DATAGRAM_SIZE = 1200;
constexpr size_t THERMAL_UDP_CHUNK_SIZE =
    THERMAL_UDP_DATAGRAM_SIZE - THERMAL_UDP_HEADER_SIZE;
constexpr size_t THERMAL_PAYLOAD_SIZE =
    THERMAL_META_SIZE + THERMAL_PIXEL_COUNT * sizeof(uint16_t);
constexpr uint16_t THERMAL_UDP_CHUNK_COUNT =
    (THERMAL_PAYLOAD_SIZE + THERMAL_UDP_CHUNK_SIZE - 1) /
    THERMAL_UDP_CHUNK_SIZE;

struct TelemetrySnapshot {
  uint32_t sequence;
  uint32_t uptimeMs;
  float respirationRate;
  float heartRate;
  uint16_t co2Ppm;
  bool pirMotion;
  bool respirationValid;
  bool heartValid;
  bool co2Valid;
  // Tri-state MR60 occupancy. `humanDetectedKnown == false` must serialize as
  // JSON null, never false: the Pi presence gate treats false as "room empty"
  // and would then suppress mmWave inference for the wrong reason.
  bool humanDetectedRaw;
  bool humanDetectedKnown;
};

struct ThermalTxFrame {
  uint32_t frameSequence;
  uint32_t uptimeMs;
  uint16_t minimumRaw;
  uint16_t maximumRaw;
  uint16_t pixels[THERMAL_PIXEL_COUNT];
};

enum class ThermalSendResult {
  Sent,
  Preempted,
  Failed,
};

SensirionI2cScd4x scd4x;
HardwareSerial mmWaveSerial(2);

// The library's own SEEED_MR60BHA2::isHumanDetected() cannot express "unknown":
// it returns false both when the room is empty and when no 0x0F09 report has
// been parsed yet, and it self-clears its validity flag on read. Overriding
// handleType() captures the report itself, so an absent report stays
// distinguishable from a negative one. The base implementation is still
// invoked, leaving library state untouched, and the base class has already
// verified both frame checksums before dispatching here.
class SafeNestMR60BHA2 : public SEEED_MR60BHA2 {
 public:
  bool handleType(uint16_t type, const uint8_t *data,
                  size_t dataLength) override {
    if (type == static_cast<uint16_t>(
                    TypeHeartBreath::ReportHumanDetection)) {
      // The vendor handler reads data[0] unguarded; refuse a truncated report
      // here instead of letting it read out of bounds.
      if (dataLength < 1) return false;
      presenceRaw_ = data[0] != 0;
      presencePending_ = true;
    }
    return SEEED_MR60BHA2::handleType(type, data, dataLength);
  }

  // Same one-shot out-parameter idiom as getBreathRate()/getHeartRate(): the
  // return value means "a new report was parsed", never "nobody is present".
  bool takePresence(bool &value) {
    if (!presencePending_) return false;
    presencePending_ = false;
    value = presenceRaw_;
    return true;
  }

 private:
  bool presenceRaw_ = false;
  bool presencePending_ = false;
};

SafeNestMR60BHA2 mmWave;
SPIClass thermalSpi(VSPI);

QueueHandle_t telemetryQueue = nullptr;
QueueHandle_t thermalQueue = nullptr;
EventGroupHandle_t networkEvents = nullptr;
SemaphoreHandle_t networkTxMutex = nullptr;
constexpr EventBits_t TCP_CRITICAL_BIT = BIT0;

uint16_t thermalCapture[THERMAL_CAPTURE_WORDS];
// These ~10 KiB objects are global on purpose. Keeping either on a task stack
// can overflow the default Arduino loop stack on a non-PSRAM ESP32.
ThermalTxFrame thermalProducerFrame;
ThermalTxFrame thermalNetworkFrame;
uint8_t thermalAddress = 0;
bool thermalStarted = false;
bool co2Started = false;
bool co2AddressPresent = false;

float respirationRate = NAN;
float heartRate = NAN;
uint16_t co2Ppm = 0;
bool pirMotion = false;
bool humanDetectedRaw = false;

uint32_t lastRespirationMs = 0;
uint32_t lastHeartMs = 0;
uint32_t lastPresenceMs = 0;
uint32_t lastCo2Ms = 0;
uint32_t lastThermalStatusPollMs = 0;
uint32_t lastPirPollMs = 0;
uint32_t lastCo2PollMs = 0;
uint32_t lastTelemetryMs = 0;
uint32_t lastHealthLogMs = 0;
uint32_t telemetrySequence = 0;
uint32_t thermalSequence = 0;
uint32_t thermalCrcErrors = 0;
uint32_t thermalRangeErrors = 0;
// Written by the network tasks on core 0 and read by loop() on core 1. Each
// counter has exactly one writer and aligned 32-bit accesses are atomic on
// Xtensa, so volatile only has to stop the compiler caching them in registers.
volatile uint32_t telemetryQueueOverwrites = 0;
volatile uint32_t thermalQueueOverwrites = 0;
volatile uint32_t tcpConnectionFailures = 0;
volatile uint32_t tcpSendFailures = 0;
volatile uint32_t thermalUdpFramesSent = 0;
volatile uint32_t thermalFramesPreempted = 0;
volatile uint32_t thermalUdpSendFailures = 0;
// Written and read only by loop() on core 1, so volatile is not warranted.
uint32_t co2DataReadyQueryFailures = 0;
uint32_t co2ReadFailures = 0;
uint32_t thermalStatusQueryFailures = 0;
uint32_t co2InitAttempts = 0;
int16_t co2LastStartError = 0;
Co2State co2State = Co2State::RETRY_WAIT;
uint32_t co2NextActionMs = 0;
uint32_t co2RetryCount = 0;
uint32_t co2ConsecutiveFailures = 0;
uint32_t mmWaveUpdateSuccesses = 0;
uint32_t mmWaveUpdateMisses = 0;
uint32_t lastMmWaveUpdateMs = 0;
uint8_t thermalUdpDatagram[THERMAL_UDP_DATAGRAM_SIZE];

// Wrap-safe periodic scheduling helper. Updating by period, rather than assigning
// now, avoids gradual drift. A long overrun is collapsed to one execution.
bool scheduleDue(uint32_t now, uint32_t &lastRun, uint32_t period) {
  if (static_cast<uint32_t>(now - lastRun) < period) return false;
  lastRun += period;
  if (static_cast<uint32_t>(now - lastRun) >= period) lastRun = now;
  return true;
}

bool isFresh(uint32_t timestamp, uint32_t now, uint32_t timeout) {
  if (timestamp == 0) return false;
  const int32_t age = static_cast<int32_t>(now - timestamp);
  return age < static_cast<int32_t>(timeout);
}

bool deadlineReached(uint32_t now, uint32_t deadline) {
  return static_cast<int32_t>(now - deadline) >= 0;
}

const char *co2StateName(Co2State state) {
  switch (state) {
    case Co2State::RETRY_WAIT:
      return "RETRY_WAIT";
    case Co2State::STOP_WAIT:
      return "STOP_WAIT";
    case Co2State::RUNNING:
      return "RUNNING";
  }
  return "UNKNOWN";
}

void initializeBootId() {
  uint32_t words[4];
  for (uint8_t index = 0; index < 4; ++index) words[index] = esp_random();
  snprintf(bootId, sizeof(bootId), "%08lx%08lx%08lx%08lx",
           static_cast<unsigned long>(words[0]),
           static_cast<unsigned long>(words[1]),
           static_cast<unsigned long>(words[2]),
           static_cast<unsigned long>(words[3]));
}

// Blocking waits are used only during one-time hardware initialization. The
// runtime loop itself remains delay-free.
void setupWait(uint32_t milliseconds) {
  vTaskDelay(pdMS_TO_TICKS(milliseconds));
}

bool i2cPresent(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

bool thermalWriteRegister(uint8_t reg, uint8_t value) {
  if (thermalAddress == 0) return false;
  Wire.beginTransmission(thermalAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool thermalReadRegister(uint8_t reg, uint8_t &value) {
  if (thermalAddress == 0) return false;
  Wire.beginTransmission(thermalAddress);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(thermalAddress, static_cast<uint8_t>(1)) != 1) {
    return false;
  }
  value = Wire.read();
  return true;
}

void initializeThermalCamera() {
  if (i2cPresent(THERMAL_ADDRESS_A)) {
    thermalAddress = THERMAL_ADDRESS_A;
  } else if (i2cPresent(THERMAL_ADDRESS_B)) {
    thermalAddress = THERMAL_ADDRESS_B;
  } else {
    Serial.println("[thermal] ERROR: I2C address 0x40/0x41 not found");
    return;
  }

  // Active-low reset. The pulse and post-reset wait are required by hardware.
  digitalWrite(PIN_THERMAL_RESET, LOW);
  delayMicroseconds(100);
  digitalWrite(PIN_THERMAL_RESET, HIGH);
  setupWait(100);

  uint8_t evkTest = 0;
  if (!thermalReadRegister(REG_EVK_TEST, evkTest)) {
    Serial.println("[thermal] ERROR: register read failed");
    return;
  }

  // Non-bridge MI48 variants require the explicit sensor power-up command.
  if (evkTest != 0xFF) {
    if (!thermalWriteRegister(REG_SENSOR_POWERUP, 0x13)) {
      Serial.println("[thermal] ERROR: power-up command failed");
      return;
    }
    setupWait(100);
  }

  const uint32_t bootStarted = millis();
  uint8_t status = STATUS_BOOTING;
  while (static_cast<uint32_t>(millis() - bootStarted) < 3000) {
    if (!thermalReadRegister(REG_STATUS, status)) {
      Serial.println("[thermal] ERROR: status read failed");
      return;
    }
    if ((status & STATUS_BOOTING) == 0) break;
    setupWait(25);
  }
  if (status & STATUS_BOOTING) {
    Serial.println("[thermal] ERROR: boot timeout");
    return;
  }

  uint8_t fw1 = 0, fw2 = 0, sensorType = 0;
  thermalReadRegister(REG_FW_VERSION_1, fw1);
  thermalReadRegister(REG_FW_VERSION_2, fw2);
  thermalReadRegister(REG_SENSOR_TYPE, sensorType);

  thermalWriteRegister(REG_FRAME_MODE, 0x00);
  setupWait(30);
  if (!thermalWriteRegister(REG_FRAME_RATE, THERMAL_FRAME_RATE_DIVIDER) ||
      !thermalWriteRegister(REG_FRAME_MODE, MODE_CONTINUOUS)) {
    Serial.println("[thermal] ERROR: continuous stream start failed");
    return;
  }

  thermalStarted = true;
  Serial.printf("[thermal] ready: addr=0x%02X type=%u fw=%u.%u.%u\n",
                static_cast<unsigned>(thermalAddress),
                static_cast<unsigned>(sensorType),
                static_cast<unsigned>((fw1 >> 4) & 0x0F),
                static_cast<unsigned>(fw1 & 0x0F),
                static_cast<unsigned>(fw2));
}

// MI48 frame CRC: CRC-16/CCITT-FALSE, polynomial 0x1021, initial 0xFFFF.
// The vendor driver calculates it over the native uint16 pixel buffer, so
// each received word is fed low byte first and then high byte.
uint16_t thermalFrameCrc(const uint16_t *pixels, size_t count) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < count; ++i) {
    const uint8_t bytes[2] = {
        static_cast<uint8_t>(pixels[i] & 0xFF),
        static_cast<uint8_t>(pixels[i] >> 8)};
    for (uint8_t value : bytes) {
      crc ^= static_cast<uint16_t>(value) << 8;
      for (uint8_t bit = 0; bit < 8; ++bit) {
        crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                             : static_cast<uint16_t>(crc << 1);
      }
    }
  }
  return crc;
}

bool thermalDataReady(uint32_t now) {
  if (digitalRead(PIN_THERMAL_READY) == HIGH) return true;

  // I2C polling is a fallback and also makes a disconnected READY wire visible.
  if (static_cast<uint32_t>(now - lastThermalStatusPollMs) < 25) return false;
  lastThermalStatusPollMs = now;
  uint8_t status = 0;
  if (!thermalReadRegister(REG_STATUS, status)) {
    ++thermalStatusQueryFailures;
    return false;
  }
  return (status & STATUS_DATA_READY) != 0;
}

void captureThermalIfReady(uint32_t now) {
  if (!thermalStarted || !thermalDataReady(now)) return;

  thermalSpi.beginTransaction(
      SPISettings(THERMAL_SPI_HZ, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_THERMAL_CS, LOW);
  delayMicroseconds(100);

  // MI48xx returns every word MSB first. Reading bytes explicitly avoids host
  // endianness ambiguity in SPI.transfer16().
  for (size_t i = 0; i < THERMAL_CAPTURE_WORDS; ++i) {
    const uint8_t highByte = thermalSpi.transfer(0x00);
    const uint8_t lowByte = thermalSpi.transfer(0x00);
    thermalCapture[i] = (static_cast<uint16_t>(highByte) << 8) | lowByte;
  }

  delayMicroseconds(100);
  digitalWrite(PIN_THERMAL_CS, HIGH);
  thermalSpi.endTransaction();

  ThermalTxFrame &frame = thermalProducerFrame;
  frame.uptimeMs = millis();
  frame.minimumRaw = UINT16_MAX;
  frame.maximumRaw = 0;

  for (size_t i = 0; i < THERMAL_PIXEL_COUNT; ++i) {
    const uint16_t raw = thermalCapture[THERMAL_HEADER_WORDS + i];
    frame.pixels[i] = raw;
    if (raw < frame.minimumRaw) frame.minimumRaw = raw;
    if (raw > frame.maximumRaw) frame.maximumRaw = raw;
  }

  const uint16_t expectedCrc = thermalCapture[7];
  const uint16_t actualCrc = thermalFrameCrc(
      thermalCapture + THERMAL_HEADER_WORDS, THERMAL_PIXEL_COUNT);
  if (actualCrc != expectedCrc) {
    ++thermalCrcErrors;
    if (thermalCrcErrors <= 3 || thermalCrcErrors % 25 == 0) {
      Serial.printf(
          "[thermal] dropped CRC frame: header=0x%04X calc=0x%04X "
          "errors=%lu\n",
          static_cast<unsigned>(expectedCrc),
          static_cast<unsigned>(actualCrc),
          static_cast<unsigned long>(thermalCrcErrors));
    }
    return;
  }

  if (thermalCapture[5] != frame.maximumRaw ||
      thermalCapture[6] != frame.minimumRaw) {
    ++thermalRangeErrors;
    if (thermalRangeErrors <= 3 || thermalRangeErrors % 25 == 0) {
      Serial.printf(
          "[thermal] dropped header-range frame: header=%u..%u "
          "calc=%u..%u errors=%lu\n",
          static_cast<unsigned>(thermalCapture[6]),
          static_cast<unsigned>(thermalCapture[5]),
          static_cast<unsigned>(frame.minimumRaw),
          static_cast<unsigned>(frame.maximumRaw),
          static_cast<unsigned long>(thermalRangeErrors));
    }
    return;
  }

  frame.frameSequence = ++thermalSequence;
  // Queue length is one, so this replaces an unsent old frame under congestion.
  xQueueOverwrite(thermalQueue, &frame);
}

void scheduleCo2Retry(uint32_t now) {
  co2Started = false;
  co2State = Co2State::RETRY_WAIT;
  co2NextActionMs = now + CO2_RETRY_PERIOD_MS;
  ++co2RetryCount;
}

void initializeCo2(uint32_t now) {
  if (co2State == Co2State::RUNNING) return;

  if (co2State == Co2State::STOP_WAIT) {
    if (!deadlineReached(now, co2NextActionMs)) return;

    co2LastStartError = scd4x.startPeriodicMeasurement();
    if (co2LastStartError != 0) {
      Serial.printf(
          "[co2] ERROR: startPeriodicMeasurement=%d; retry in %lu ms\n",
          static_cast<int>(co2LastStartError),
          static_cast<unsigned long>(CO2_RETRY_PERIOD_MS));
      scheduleCo2Retry(now);
      return;
    }

    co2Started = true;
    co2State = Co2State::RUNNING;
    co2NextActionMs = 0;
    co2ConsecutiveFailures = 0;
    lastCo2PollMs = now;
    Serial.printf(
        "[co2] ready attempt=%lu: first measurement takes about 5 seconds\n",
        static_cast<unsigned long>(co2InitAttempts));
    return;
  }

  if (!deadlineReached(now, co2NextActionMs)) return;

  ++co2InitAttempts;
  co2AddressPresent = i2cPresent(SCD4X_ADDRESS);
  if (!co2AddressPresent) {
    co2LastStartError = -1;
    Serial.printf("[co2] address 0x62 not found; retry in %lu ms\n",
                  static_cast<unsigned long>(CO2_RETRY_PERIOD_MS));
    scheduleCo2Retry(now);
    return;
  }

  Serial.printf("[co2] retry attempt=%lu probe=ok\n",
                static_cast<unsigned long>(co2InitAttempts));
  scd4x.begin(Wire, SCD4X_ADDRESS);
  scd4x.stopPeriodicMeasurement();
  co2State = Co2State::STOP_WAIT;
  co2NextActionMs = now + CO2_STOP_WAIT_MS;
  Serial.printf("[co2] stop sent; start scheduled in %lu ms\n",
                static_cast<unsigned long>(CO2_STOP_WAIT_MS));
}

void recordCo2RuntimeFailure(uint32_t now) {
  ++co2ConsecutiveFailures;
  if (co2ConsecutiveFailures < CO2_MAX_CONSECUTIVE_FAILURES) return;

  Serial.printf(
      "[co2] runtime failures=%lu; scheduling reinitialization in %lu ms\n",
      static_cast<unsigned long>(co2ConsecutiveFailures),
      static_cast<unsigned long>(CO2_RETRY_PERIOD_MS));
  scheduleCo2Retry(now);
}

void pollCo2(uint32_t now) {
  initializeCo2(now);
  if (!co2Started || !scheduleDue(now, lastCo2PollMs, CO2_POLL_PERIOD_MS)) {
    return;
  }

  bool ready = false;
  if (scd4x.getDataReadyStatus(ready) != 0) {
    ++co2DataReadyQueryFailures;
    recordCo2RuntimeFailure(now);
    return;
  }
  if (!ready) return;

  uint16_t newCo2 = 0;
  float temperature = NAN;
  float humidity = NAN;
  if (scd4x.readMeasurement(newCo2, temperature, humidity) != 0) {
    ++co2ReadFailures;
    recordCo2RuntimeFailure(now);
    return;
  }
  if (newCo2 == 0) return;

  co2Ppm = newCo2;
  lastCo2Ms = now;
  co2ConsecutiveFailures = 0;
}

void pollMmWave(uint32_t now) {
  // timeout=0 makes the library consume currently buffered UART data without
  // waiting. Repeated loop calls drain all queued radar frames.
  if (!mmWave.update(0)) {
    ++mmWaveUpdateMisses;
    return;
  }
  ++mmWaveUpdateSuccesses;
  lastMmWaveUpdateMs = now;

  float value = 0.0f;
  if (mmWave.getBreathRate(value) && isfinite(value)) {
    respirationRate = value;
    lastRespirationMs = now;
  }
  if (mmWave.getHeartRate(value) && isfinite(value)) {
    heartRate = value;
    lastHeartMs = now;
  }

  // MR60's own normalized occupancy boolean. It is recorded verbatim: no
  // occupancy threshold is derived from breath rate or any other signal, and
  // no majority-vote smoothing is applied, because the wire contract carries
  // human_detected_raw only. Staleness is judged at publish time so a radar
  // that stops reporting eventually degrades this to null.
  bool presenceValue = false;
  if (mmWave.takePresence(presenceValue)) {
    humanDetectedRaw = presenceValue;
    lastPresenceMs = now;
  }
}

void publishTelemetrySnapshot(uint32_t now) {
  if (!scheduleDue(now, lastTelemetryMs, TELEMETRY_PERIOD_MS)) return;

  TelemetrySnapshot snapshot{};
  snapshot.sequence = ++telemetrySequence;
  snapshot.uptimeMs = now;
  snapshot.respirationRate = respirationRate;
  snapshot.heartRate = heartRate;
  snapshot.co2Ppm = co2Ppm;
  snapshot.pirMotion = pirMotion;
  snapshot.respirationValid = isFresh(lastRespirationMs, now, MMWAVE_STALE_MS);
  snapshot.heartValid = isFresh(lastHeartMs, now, MMWAVE_STALE_MS);
  snapshot.co2Valid = isFresh(lastCo2Ms, now, CO2_STALE_MS);
  // isFresh() also rejects the never-observed case (lastPresenceMs == 0), so a
  // node whose radar never reported occupancy publishes null rather than false.
  snapshot.humanDetectedRaw = humanDetectedRaw;
  snapshot.humanDetectedKnown = isFresh(lastPresenceMs, now,
                                        PRESENCE_MAX_AGE_MS);
  xQueueOverwrite(telemetryQueue, &snapshot);
}

// Big-endian integer encoders keep the protocol independent of CPU endianness.
void putU16(uint8_t *destination, uint16_t value) {
  destination[0] = static_cast<uint8_t>(value >> 8);
  destination[1] = static_cast<uint8_t>(value);
}

void putU32(uint8_t *destination, uint32_t value) {
  destination[0] = static_cast<uint8_t>(value >> 24);
  destination[1] = static_cast<uint8_t>(value >> 16);
  destination[2] = static_cast<uint8_t>(value >> 8);
  destination[3] = static_cast<uint8_t>(value);
}

void makePacketHeader(uint8_t *header, uint8_t type, uint32_t sequence,
                      uint32_t payloadLength) {
  memcpy(header, "SNST", 4);
  header[4] = PROTOCOL_VERSION;
  header[5] = type;
  putU16(header + 6, 0);  // flags: reserved for protocol v1
  putU32(header + 8, sequence);
  putU32(header + 12, payloadLength);
}

// Runs only in the network task, so a slow peer can never stall sensor capture.
bool writeAll(WiFiClient &client, const uint8_t *data, size_t length) {
  constexpr size_t CHUNK_BYTES = 512;
  constexpr uint32_t TIMEOUT_MS = 5000;

  size_t sent = 0;
  uint32_t lastProgress = millis();

  while (sent < length) {
    if (!client.connected()) return false;

    const size_t remaining = length - sent;
    const size_t chunk =
        remaining > CHUNK_BYTES ? CHUNK_BYTES : remaining;
    const size_t written = client.write(data + sent, chunk);

    if (written > 0) {
      sent += written;
      lastProgress = millis();
    } else {
      if (static_cast<uint32_t>(millis() - lastProgress) > TIMEOUT_MS) {
        return false;
      }
      vTaskDelay(pdMS_TO_TICKS(2));
    }
  }

  return true;
}

bool beginTcpCritical() {
  xEventGroupSetBits(networkEvents, TCP_CRITICAL_BIT);
  if (xSemaphoreTake(networkTxMutex, portMAX_DELAY) == pdTRUE) return true;
  xEventGroupClearBits(networkEvents, TCP_CRITICAL_BIT);
  return false;
}

void endTcpCritical() {
  xSemaphoreGive(networkTxMutex);
  xEventGroupClearBits(networkEvents, TCP_CRITICAL_BIT);
}

void formatNullableFloat(char *output, size_t outputSize, bool valid,
                         float value) {
  if (valid && isfinite(value)) {
    const int written = snprintf(output, outputSize, "%.2f", value);
    // A truncated number stays syntactically valid JSON but carries the wrong
    // magnitude, so fail closed to null rather than publish it.
    if (written > 0 && static_cast<size_t>(written) < outputSize) return;
  }
  strlcpy(output, "null", outputSize);
}

bool sendTelemetry(WiFiClient &client, const TelemetrySnapshot &snapshot,
                   size_t &payloadLength) {
  payloadLength = 0;
  char respiration[20], heart[20], co2[6];
  formatNullableFloat(respiration, sizeof(respiration),
                      snapshot.respirationValid, snapshot.respirationRate);
  formatNullableFloat(heart, sizeof(heart), snapshot.heartValid,
                      snapshot.heartRate);
  if (snapshot.co2Valid) {
    snprintf(co2, sizeof(co2), "%u", static_cast<unsigned>(snapshot.co2Ppm));
  } else {
    strlcpy(co2, "null", sizeof(co2));
  }

  const char *humanDetectedText = snapshot.humanDetectedKnown
                                      ? (snapshot.humanDetectedRaw ? "true"
                                                                   : "false")
                                      : "null";

  // The LCD telemetry contract stays intentionally small. Diagnostics remain
  // available through the rate-limited Serial health log below.
  char json[512];
  const int length = snprintf(
      json, sizeof(json),
      "{\"schema\":\"safenest.telemetry.v1\",\"device_id\":\"%s\","
      "\"boot_id\":\"%s\",\"seq\":%lu,\"uptime_ms\":%lu,"
      "\"resp_rate_bpm\":%s,\"heart_rate_bpm\":%s,\"co2_ppm\":%s,"
      "\"pir_motion\":%s,"
      "\"valid\":{\"respiration\":%s,\"heart\":%s,\"co2\":%s},"
      "\"mmwave\":{\"human_detected_raw\":%s}}",
      DEVICE_ID, bootId, static_cast<unsigned long>(snapshot.sequence),
      static_cast<unsigned long>(snapshot.uptimeMs), respiration, heart, co2,
      snapshot.pirMotion ? "true" : "false",
      snapshot.respirationValid ? "true" : "false",
      snapshot.heartValid ? "true" : "false",
      snapshot.co2Valid ? "true" : "false", humanDetectedText);
  if (length <= 0 || static_cast<size_t>(length) >= sizeof(json)) return false;

  payloadLength = static_cast<size_t>(length);
  uint8_t packet[PACKET_HEADER_SIZE + sizeof(json)];
  makePacketHeader(packet, PACKET_TELEMETRY_JSON, snapshot.sequence,
                   static_cast<uint32_t>(length));
  memcpy(packet + PACKET_HEADER_SIZE, json, payloadLength);

  return writeAll(client, packet, PACKET_HEADER_SIZE + payloadLength);
}

uint8_t thermalPayloadByte(const ThermalTxFrame &frame, const uint8_t *meta,
                           size_t offset) {
  if (offset < THERMAL_META_SIZE) return meta[offset];
  const size_t pixelByte = offset - THERMAL_META_SIZE;
  const uint16_t pixel = frame.pixels[pixelByte / 2];
  return (pixelByte & 1) ? static_cast<uint8_t>(pixel)
                         : static_cast<uint8_t>(pixel >> 8);
}

uint32_t thermalFrameCrc32(const ThermalTxFrame &frame, const uint8_t *meta) {
  uint32_t crc = 0xFFFFFFFF;
  for (size_t offset = 0; offset < THERMAL_PAYLOAD_SIZE; ++offset) {
    crc ^= thermalPayloadByte(frame, meta, offset);
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1) ^ (0xEDB88320U & (0U - (crc & 1U)));
    }
  }
  return ~crc;
}

ThermalSendResult sendThermalUdp(WiFiUDP &udp,
                                 const ThermalTxFrame &frame) {
  constexpr TickType_t MUTEX_TIMEOUT = pdMS_TO_TICKS(1000);
  uint8_t meta[THERMAL_META_SIZE];
  putU16(meta + 0, static_cast<uint16_t>(THERMAL_WIDTH));
  putU16(meta + 2, static_cast<uint16_t>(THERMAL_HEIGHT));
  putU32(meta + 4, frame.frameSequence);
  putU32(meta + 8, frame.uptimeMs);
  putU16(meta + 12, frame.minimumRaw);
  putU16(meta + 14, frame.maximumRaw);
  const uint32_t crc32 = thermalFrameCrc32(frame, meta);

  for (uint16_t chunkIndex = 0; chunkIndex < THERMAL_UDP_CHUNK_COUNT;
       ++chunkIndex) {
    if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0) {
      return ThermalSendResult::Preempted;
    }

    const size_t offset = chunkIndex * THERMAL_UDP_CHUNK_SIZE;
    const uint16_t length = static_cast<uint16_t>(
        min(THERMAL_UDP_CHUNK_SIZE, THERMAL_PAYLOAD_SIZE - offset));
    uint8_t *header = thermalUdpDatagram;
    memcpy(header, THERMAL_UDP_MAGIC, 4);
    header[4] = THERMAL_UDP_VERSION;
    header[5] = PACKET_THERMAL_U16_BE;
    putU16(header + 6, static_cast<uint16_t>(THERMAL_UDP_HEADER_SIZE));
    putU32(header + 8, frame.frameSequence);
    putU16(header + 12, chunkIndex);
    putU16(header + 14, THERMAL_UDP_CHUNK_COUNT);
    putU32(header + 16, static_cast<uint32_t>(THERMAL_PAYLOAD_SIZE));
    putU32(header + 20, static_cast<uint32_t>(offset));
    putU16(header + 24, length);
    putU16(header + 26, 0);
    putU32(header + 28, crc32);
    for (uint16_t index = 0; index < length; ++index) {
      thermalUdpDatagram[THERMAL_UDP_HEADER_SIZE + index] =
          thermalPayloadByte(frame, meta, offset + index);
    }

    if (xSemaphoreTake(networkTxMutex, MUTEX_TIMEOUT) != pdTRUE) {
      return ThermalSendResult::Preempted;
    }
    if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0) {
      xSemaphoreGive(networkTxMutex);
      return ThermalSendResult::Preempted;
    }

    const bool sent =
        udp.beginPacket(RPI_HOST, THERMAL_UDP_PORT) &&
        udp.write(thermalUdpDatagram, THERMAL_UDP_HEADER_SIZE + length) ==
            THERMAL_UDP_HEADER_SIZE + length &&
        udp.endPacket() == 1;
    // Capture a TCP request that arrived while this datagram held the mutex.
    // After give, the higher-priority TCP task may run and clear the bit before
    // this task resumes, so sampling only at the next chunk would miss it.
    const bool preemptedDuringSend =
        (xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0;
    xSemaphoreGive(networkTxMutex);
    if (!sent) return ThermalSendResult::Failed;
    if (preemptedDuringSend) return ThermalSendResult::Preempted;

    vTaskDelay(pdMS_TO_TICKS(2));
  }
  return ThermalSendResult::Sent;
}

void telemetryTcpTask(void *parameter) {
  (void)parameter;
  WiFiClient client;
  TelemetrySnapshot telemetry{};
  uint32_t lastDequeuedSequence = 0;
  uint32_t lastNetworkLogMs = 0;
  uint32_t lastConnectDurationMs = 0;

  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      if (client.connected() && beginTcpCritical()) {
        client.stop();
        endTcpCritical();
      }
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }

    if (!client.connected()) {
      Serial.printf("[network] connecting to %s:%u\n", RPI_HOST, RPI_PORT);
      bool connected = false;
      if (beginTcpCritical()) {
        const uint32_t connectStartedMs = millis();
        connected = client.connect(RPI_HOST, RPI_PORT, 1500);
        lastConnectDurationMs = millis() - connectStartedMs;
        if (!connected) client.stop();
        endTcpCritical();
      }
      if (!connected) {
        tcpConnectionFailures = tcpConnectionFailures + 1;
        vTaskDelay(pdMS_TO_TICKS(1000));
        continue;
      }
      client.setNoDelay(true);
      Serial.println("[network] Raspberry Pi connected");
    }

    // Scalar telemetry has priority and is small.
    if (xQueueReceive(telemetryQueue, &telemetry, 0) == pdTRUE) {
      telemetryQueueOverwrites = telemetryQueueOverwrites +
                                 telemetry.sequence - lastDequeuedSequence - 1;
      lastDequeuedSequence = telemetry.sequence;
      size_t jsonPayloadLength = 0;
      bool sent = false;
      uint32_t writeDurationMs = 0;
      if (beginTcpCritical()) {
        const uint32_t writeStartedMs = millis();
        sent = sendTelemetry(client, telemetry, jsonPayloadLength);
        writeDurationMs = millis() - writeStartedMs;
        if (!sent) client.stop();
        endTcpCritical();
      }

      if (!sent) tcpSendFailures = tcpSendFailures + 1;

      const uint32_t now = millis();
      if (lastNetworkLogMs == 0 ||
          static_cast<uint32_t>(now - lastNetworkLogMs) >=
              HEALTH_LOG_PERIOD_MS) {
        Serial.printf(
            "[network] tcp connect_ms=%lu write_ms=%lu seq=%lu "
            "json_bytes=%u tcp_send_failures=%lu thermal_preemptions=%lu "
            "thermal_udp_failures=%lu\n",
            static_cast<unsigned long>(lastConnectDurationMs),
            static_cast<unsigned long>(writeDurationMs),
            static_cast<unsigned long>(telemetry.sequence),
            static_cast<unsigned>(jsonPayloadLength),
            static_cast<unsigned long>(tcpSendFailures),
            static_cast<unsigned long>(thermalFramesPreempted),
            static_cast<unsigned long>(thermalUdpSendFailures));
        lastNetworkLogMs = now;
      }

      if (!sent) {
        continue;
      }
    }

    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

void thermalUdpTask(void *parameter) {
  (void)parameter;
  WiFiUDP udp;
  bool udpStarted = false;
  uint32_t lastDequeuedSequence = 0;
  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      if (udpStarted) {
        udp.stop();
        udpStarted = false;
      }
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    if (!udpStarted) {
      udpStarted = udp.begin(0);
      if (!udpStarted) {
        vTaskDelay(pdMS_TO_TICKS(250));
        continue;
      }
    }
    if (xQueueReceive(thermalQueue, &thermalNetworkFrame, 0) == pdTRUE) {
      thermalQueueOverwrites = thermalQueueOverwrites +
                               thermalNetworkFrame.frameSequence -
                               lastDequeuedSequence - 1;
      lastDequeuedSequence = thermalNetworkFrame.frameSequence;
      switch (sendThermalUdp(udp, thermalNetworkFrame)) {
        case ThermalSendResult::Sent:
          thermalUdpFramesSent = thermalUdpFramesSent + 1;
          break;
        case ThermalSendResult::Preempted:
          thermalFramesPreempted = thermalFramesPreempted + 1;
          break;
        case ThermalSendResult::Failed:
          thermalUdpSendFailures = thermalUdpSendFailures + 1;
          break;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

void logHealth(uint32_t now) {
  if (!scheduleDue(now, lastHealthLogMs, HEALTH_LOG_PERIOD_MS)) return;
  Serial.printf(
      "[health] wifi=%s rpi=%s resp=%.1f heart=%.1f co2=%u pir=%d "
      "co2_state=%s co2_started=%d co2_probe=%d co2_start=%d "
      "co2_init=%lu co2_retry=%lu co2_consecutive=%lu "
      "co2_next_retry_ms=%lu co2_dr_fail=%lu co2_rd_fail=%lu "
      "co2_age_ms=%ld "
      "mmw_uart=%u mmw_ok=%lu mmw_miss=%lu mmw_age_ms=%ld "
      "telemetry_queue_overwrites=%lu thermal_queue_overwrites=%lu "
      "tcp_connection_failures=%lu tcp_send_failures=%lu "
      "thermal_frames=%lu crc_errors=%lu range_errors=%lu "
      "thermal_status_failures=%lu thermal_preemptions=%lu "
      "udp_sent=%lu udp_failed=%lu "
      "free_heap=%lu\n",
      WiFi.status() == WL_CONNECTED ? "up" : "down", RPI_HOST,
      respirationRate, heartRate, static_cast<unsigned>(co2Ppm),
      pirMotion ? 1 : 0,
      co2StateName(co2State),
      co2Started ? 1 : 0, co2AddressPresent ? 1 : 0,
      static_cast<int>(co2LastStartError),
      static_cast<unsigned long>(co2InitAttempts),
      static_cast<unsigned long>(co2RetryCount),
      static_cast<unsigned long>(co2ConsecutiveFailures),
      static_cast<unsigned long>(
          co2State == Co2State::RETRY_WAIT &&
                  !deadlineReached(now, co2NextActionMs)
              ? co2NextActionMs - now
              : 0),
      static_cast<unsigned long>(co2DataReadyQueryFailures),
      static_cast<unsigned long>(co2ReadFailures),
      lastCo2Ms == 0 ? -1L : static_cast<long>(now - lastCo2Ms),
      static_cast<unsigned>(mmWaveSerial.available()),
      static_cast<unsigned long>(mmWaveUpdateSuccesses),
      static_cast<unsigned long>(mmWaveUpdateMisses),
      lastMmWaveUpdateMs == 0
          ? -1L
          : static_cast<long>(now - lastMmWaveUpdateMs),
      static_cast<unsigned long>(telemetryQueueOverwrites),
      static_cast<unsigned long>(thermalQueueOverwrites),
      static_cast<unsigned long>(tcpConnectionFailures),
      static_cast<unsigned long>(tcpSendFailures),
      static_cast<unsigned long>(thermalSequence),
      static_cast<unsigned long>(thermalCrcErrors),
      static_cast<unsigned long>(thermalRangeErrors),
      static_cast<unsigned long>(thermalStatusQueryFailures),
      static_cast<unsigned long>(thermalFramesPreempted),
      static_cast<unsigned long>(thermalUdpFramesSent),
      static_cast<unsigned long>(thermalUdpSendFailures),
      static_cast<unsigned long>(ESP.getFreeHeap()));
}

void setup() {
  Serial.begin(USB_BAUD);
  setupWait(500);
  Serial.println("\nSafeNest ESP32 sensor node starting");
  initializeBootId();
  Serial.printf("[identity] device=%s boot=%s firmware=%s diag=%s reset=%d\n",
                DEVICE_ID, bootId, NODE_FIRMWARE_VERSION,
                DIAGNOSTIC_BUILD_ID, static_cast<int>(esp_reset_reason()));

  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_THERMAL_CS, OUTPUT);
  digitalWrite(PIN_THERMAL_CS, HIGH);
  pinMode(PIN_THERMAL_READY, INPUT);
  pinMode(PIN_THERMAL_RESET, OUTPUT);
  digitalWrite(PIN_THERMAL_RESET, HIGH);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(100000);
  thermalSpi.begin(PIN_THERMAL_SCLK, PIN_THERMAL_MISO,
                   PIN_THERMAL_MOSI, PIN_THERMAL_CS);

  // setPins() before the library's begin() makes its pin-less Serial.begin()
  // retain GPIO16/17 on both Arduino-ESP32 core 2.x and 3.x.
  mmWaveSerial.setPins(PIN_MMWAVE_RX, PIN_MMWAVE_TX);
  mmWave.begin(&mmWaveSerial, MMWAVE_BAUD, 0);

  telemetryQueue = xQueueCreate(1, sizeof(TelemetrySnapshot));
  thermalQueue = xQueueCreate(1, sizeof(ThermalTxFrame));
  networkEvents = xEventGroupCreate();
  networkTxMutex = xSemaphoreCreateMutex();
  if (telemetryQueue == nullptr || thermalQueue == nullptr ||
      networkEvents == nullptr || networkTxMutex == nullptr) {
    Serial.println("[fatal] queue or network synchronization allocation failed");
    while (true) vTaskDelay(portMAX_DELAY);
  }

  initializeThermalCamera();
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // lower latency for the continuous thermal stream
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[wifi] connecting to %s asynchronously\n", WIFI_SSID);

  // Priority alone cannot preempt datagrams already queued by lwIP, so the
  // per-datagram mutex and TCP critical bit remain required for bounded access.
  xTaskCreatePinnedToCore(telemetryTcpTask, "telemetry-tcp", 8192, nullptr, 2,
                          nullptr, 0);
  xTaskCreatePinnedToCore(thermalUdpTask, "thermal-udp", 8192, nullptr, 1,
                          nullptr, 0);
}

void loop() {
  const uint32_t now = millis();

  pollMmWave(now);
  pollCo2(now);
  captureThermalIfReady(now);

  if (scheduleDue(now, lastPirPollMs, PIR_PERIOD_MS)) {
    pirMotion = digitalRead(PIN_PIR) == HIGH;
  }

  publishTelemetrySnapshot(now);
  logHealth(now);

  // Cooperative yield only; there is intentionally no delay() in runtime.
  taskYIELD();
}
