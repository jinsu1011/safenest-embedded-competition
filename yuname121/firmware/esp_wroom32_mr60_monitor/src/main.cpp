#include <Arduino.h>

#include <cmath>
#include <cstring>

namespace {

constexpr uint32_t kUsbBaud = 115200;
constexpr uint32_t kRadarBaud = 115200;
constexpr int kRadarRxPin = 16;
constexpr int kRadarTxPin = 17;
constexpr size_t kHeaderSize = 8;
constexpr size_t kMaxDataSize = 512;
constexpr size_t kMaxFrameSize = kHeaderSize + kMaxDataSize + 1;
constexpr uint8_t kSof = 0x01;
constexpr uint32_t kTelemetryIntervalMs = 100;

constexpr uint16_t kTypePhases = 0x0A13;
constexpr uint16_t kTypeBreath = 0x0A14;
constexpr uint16_t kTypeHeart = 0x0A15;
constexpr uint16_t kTypeDistance = 0x0A16;
constexpr uint16_t kTypePresence = 0x0F09;
constexpr uint16_t kTypeFirmware = 0xFFFF;

HardwareSerial radarSerial(2);
uint8_t frameBuffer[kMaxFrameSize];
size_t frameLength = 0;
size_t expectedLength = 0;

uint32_t sequence = 0;
uint32_t validFrames = 0;
uint32_t checksumErrors = 0;
uint32_t parseErrors = 0;
uint32_t lastTelemetryMs = 0;

bool presenceKnown = false;
bool presenceRaw = false;
uint32_t presenceUpdatedMs = 0;
float distanceRaw = NAN;
float breathRaw = NAN;
float heartRaw = NAN;
float totalPhase = NAN;
float breathPhase = NAN;
float heartPhase = NAN;
uint32_t distanceUpdatedMs = 0;
uint32_t breathUpdatedMs = 0;
uint32_t heartUpdatedMs = 0;
uint32_t phasesUpdatedMs = 0;
uint32_t firmwareRaw = 0;
bool firmwareKnown = false;

uint8_t checksum(const uint8_t* data, size_t length) {
  uint8_t value = 0;
  for (size_t i = 0; i < length; ++i) value ^= data[i];
  return static_cast<uint8_t>(~value);
}

float readFloat(const uint8_t* data) {
  float value;
  memcpy(&value, data, sizeof(value));
  return value;
}

uint32_t readU32(const uint8_t* data) {
  uint32_t value;
  memcpy(&value, data, sizeof(value));
  return value;
}

void printNullableFloat(float value) {
  if (std::isfinite(value)) Serial.print(value, 2);
  else Serial.print("null");
}

void printAge(bool known, uint32_t updatedAt, uint32_t now) {
  if (known) Serial.print(now - updatedAt);
  else Serial.print("null");
}

void emitTelemetry(uint32_t now) {
  Serial.printf(
      "{\"schema_version\":\"1.0\",\"device_id\":\"safenest-node-01\","
      "\"seq\":%lu,\"ts_monotonic_ms\":%lu,"
      "\"uart_frame_ok\":true,\"checksum_ok\":true,"
      "\"uart_frames_total\":%lu,\"checksum_errors\":%lu,"
      "\"parse_errors\":%lu,\"human_detected_raw\":",
      static_cast<unsigned long>(sequence++), static_cast<unsigned long>(now),
      static_cast<unsigned long>(validFrames),
      static_cast<unsigned long>(checksumErrors),
      static_cast<unsigned long>(parseErrors));
  if (presenceKnown) Serial.print(presenceRaw ? "true" : "false");
  else Serial.print("null");
  Serial.print(",\"presence_age_ms\":");
  printAge(presenceKnown, presenceUpdatedMs, now);
  Serial.print(",\"distance_cm_raw\":");
  printNullableFloat(distanceRaw);
  Serial.print(",\"distance_age_ms\":");
  printAge(std::isfinite(distanceRaw), distanceUpdatedMs, now);
  Serial.print(",\"breath_rate_raw\":");
  printNullableFloat(breathRaw);
  Serial.print(",\"breath_age_ms\":");
  printAge(std::isfinite(breathRaw), breathUpdatedMs, now);
  Serial.print(",\"heart_rate_raw\":");
  printNullableFloat(heartRaw);
  Serial.print(",\"heart_age_ms\":");
  printAge(std::isfinite(heartRaw), heartUpdatedMs, now);
  Serial.print(",\"total_phase\":");
  printNullableFloat(totalPhase);
  Serial.print(",\"breath_phase\":");
  printNullableFloat(breathPhase);
  Serial.print(",\"heart_phase\":");
  printNullableFloat(heartPhase);
  Serial.print(",\"phase_age_ms\":");
  printAge(std::isfinite(totalPhase), phasesUpdatedMs, now);
  Serial.print(",\"firmware_version\":");
  if (firmwareKnown) Serial.printf("\"0x%08lX\"", static_cast<unsigned long>(firmwareRaw));
  else Serial.print("null");
  Serial.println(",\"sensor_state\":\"RAW\"}");
}

void handleValidFrame(uint16_t type, const uint8_t* data, size_t dataLength,
                      uint32_t now) {
  switch (type) {
    case kTypePhases:
      if (dataLength < 12) { ++parseErrors; return; }
      totalPhase = readFloat(data);
      breathPhase = readFloat(data + 4);
      heartPhase = readFloat(data + 8);
      phasesUpdatedMs = now;
      break;
    case kTypeBreath:
      if (dataLength < 4) { ++parseErrors; return; }
      breathRaw = readFloat(data);
      breathUpdatedMs = now;
      break;
    case kTypeHeart:
      if (dataLength < 4) { ++parseErrors; return; }
      heartRaw = readFloat(data);
      heartUpdatedMs = now;
      break;
    case kTypeDistance:
      if (dataLength < 8) { ++parseErrors; return; }
      distanceRaw = readU32(data) ? readFloat(data + 4) : NAN;
      distanceUpdatedMs = now;
      break;
    case kTypePresence:
      if (dataLength < 1) { ++parseErrors; return; }
      presenceKnown = true;
      presenceRaw = data[0] != 0;
      presenceUpdatedMs = now;
      break;
    case kTypeFirmware:
      if (dataLength < 4) { ++parseErrors; return; }
      firmwareRaw = readU32(data);
      firmwareKnown = true;
      break;
    default:
      break;
  }
  ++validFrames;
}

void processFrame(uint32_t now) {
  const size_t dataLength = (static_cast<size_t>(frameBuffer[3]) << 8) |
                            static_cast<size_t>(frameBuffer[4]);
  const bool headerOk = checksum(frameBuffer, 7) == frameBuffer[7];
  const bool dataOk = checksum(frameBuffer + kHeaderSize, dataLength) ==
                      frameBuffer[kHeaderSize + dataLength];
  if (!headerOk || !dataOk) { ++checksumErrors; return; }
  const uint16_t type = (static_cast<uint16_t>(frameBuffer[5]) << 8) |
                        frameBuffer[6];
  handleValidFrame(type, frameBuffer + kHeaderSize, dataLength, now);
}

void consumeByte(uint8_t value, uint32_t now) {
  if (frameLength == 0) {
    if (value == kSof) frameBuffer[frameLength++] = value;
    return;
  }
  if (frameLength >= kMaxFrameSize) {
    ++parseErrors;
    frameLength = 0;
    expectedLength = 0;
    return;
  }
  frameBuffer[frameLength++] = value;
  if (frameLength == kHeaderSize) {
    const size_t dataLength = (static_cast<size_t>(frameBuffer[3]) << 8) |
                              frameBuffer[4];
    if (dataLength > kMaxDataSize) {
      ++parseErrors;
      frameLength = 0;
      expectedLength = 0;
      return;
    }
    expectedLength = kHeaderSize + dataLength + 1;
  }
  if (expectedLength != 0 && frameLength == expectedLength) {
    processFrame(now);
    frameLength = 0;
    expectedLength = 0;
  }
}

}  // namespace

void setup() {
  Serial.begin(kUsbBaud);
  delay(1000);
  radarSerial.begin(kRadarBaud, SERIAL_8N1, kRadarRxPin, kRadarTxPin);
  Serial.println("{\"event\":\"boot\",\"board\":\"esp-wroom-32\","
                 "\"collector\":\"tiny-frame-v1\",\"radar_uart\":\"UART2\","
                 "\"rx_gpio\":16,\"tx_gpio\":17,\"baud\":115200}");
}

void loop() {
  while (radarSerial.available() > 0) {
    consumeByte(static_cast<uint8_t>(radarSerial.read()), millis());
  }
  const uint32_t now = millis();
  if (now - lastTelemetryMs >= kTelemetryIntervalMs) {
    lastTelemetryMs = now;
    emitTelemetry(now);
  }
  delay(1);
}
