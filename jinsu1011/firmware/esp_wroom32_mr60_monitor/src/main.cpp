#include <Arduino.h>

#include <cmath>
#include <cstring>

#include "mmwave_config.h"

namespace {

using namespace safenest::mmwave_config;

constexpr size_t kHeaderSize = 8;
constexpr size_t kMaxDataSize = 512;
constexpr size_t kMaxFrameSize = kHeaderSize + kMaxDataSize + 1;
constexpr uint8_t kSof = 0x01;
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
uint32_t lastValidFrameMs = 0;
uint8_t consecutiveUartErrors = 0;

bool presenceKnown = false;
bool presenceRaw = false;
bool presenceStableKnown = false;
bool presenceStable = false;
uint8_t presenceHistory = 0;
uint8_t presenceSamples = 0;
uint32_t presenceUpdatedMs = 0;
uint32_t stablePresenceStartedMs = 0;

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

enum class SensorState { kWarmup, kValid, kUnknown, kFault };

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

bool fresh(uint32_t updatedAt, uint32_t maxAge, uint32_t now) {
  return updatedAt != 0 && now - updatedAt <= maxAge;
}

void recordUartError() {
  if (consecutiveUartErrors < UINT8_MAX) ++consecutiveUartErrors;
}

void recordValidFrame(uint32_t now) {
  ++validFrames;
  consecutiveUartErrors = 0;
  lastValidFrameMs = now;
}

void updateStablePresence(bool raw, uint32_t now) {
  presenceHistory = static_cast<uint8_t>(
      ((presenceHistory << 1U) | (raw ? 1U : 0U)) &
      ((1U << kPresenceWindowSamples) - 1U));
  if (presenceSamples < kPresenceWindowSamples) ++presenceSamples;
  if (presenceSamples < kPresenceWindowSamples) {
    presenceStableKnown = false;
    return;
  }
  uint8_t trueCount = 0;
  for (uint8_t i = 0; i < kPresenceWindowSamples; ++i) {
    trueCount += (presenceHistory >> i) & 1U;
  }
  const bool previous = presenceStable;
  if (trueCount >= kPresenceRequiredTrue) {
    presenceStable = true;
    presenceStableKnown = true;
  } else if (kPresenceWindowSamples - trueCount >= kPresenceRequiredFalse) {
    presenceStable = false;
    presenceStableKnown = true;
  } else {
    presenceStableKnown = false;
  }
  if (presenceStableKnown && presenceStable && !previous) {
    stablePresenceStartedMs = now;
  } else if (presenceStableKnown && !presenceStable) {
    stablePresenceStartedMs = 0;
  }
}

void printNullableFloat(float value) {
  if (std::isfinite(value)) Serial.print(value, 2);
  else Serial.print("null");
}

void printNullableBool(bool known, bool value) {
  if (known) Serial.print(value ? "true" : "false");
  else Serial.print("null");
}

void printAge(bool known, uint32_t updatedAt, uint32_t now) {
  if (known && updatedAt != 0) Serial.print(now - updatedAt);
  else Serial.print("null");
}

SensorState sensorState(uint32_t now, const char** errorCode) {
  const bool uartTimedOut =
      (lastValidFrameMs == 0 && now > kFrameTimeoutMs) ||
      (lastValidFrameMs != 0 && now - lastValidFrameMs > kFrameTimeoutMs);
  if (uartTimedOut) {
    *errorCode = "UART_FRAME_TIMEOUT";
    return SensorState::kFault;
  }
  if (consecutiveUartErrors >= kFaultConsecutiveUartErrors) {
    *errorCode = "UART_CONSECUTIVE_ERRORS";
    return SensorState::kFault;
  }
  if (!presenceStableKnown) {
    *errorCode = "PRESENCE_WINDOW_NOT_READY";
    return SensorState::kUnknown;
  }
  if (!fresh(presenceUpdatedMs, kFrameTimeoutMs, now)) {
    *errorCode = "PRESENCE_STALE";
    return SensorState::kUnknown;
  }
  if (!presenceStable) {
    *errorCode = "PRESENCE_NOT_DETECTED";
    return SensorState::kUnknown;
  }
  const bool distanceValid =
      std::isfinite(distanceRaw) && distanceRaw >= kDistanceMinCm &&
      distanceRaw <= kDistanceMaxCm &&
      fresh(distanceUpdatedMs, kDistanceMaxAgeMs, now);
  if (!distanceValid) {
    *errorCode = "DISTANCE_INVALID_OR_STALE";
    return SensorState::kUnknown;
  }
  const bool phaseValid =
      std::isfinite(totalPhase) && std::isfinite(breathPhase) &&
      std::isfinite(heartPhase) && fresh(phasesUpdatedMs, kPhaseMaxAgeMs, now);
  if (!phaseValid) {
    *errorCode = "PHASE_INVALID_OR_STALE";
    return SensorState::kUnknown;
  }
  if (stablePresenceStartedMs == 0 ||
      now - stablePresenceStartedMs < kWarmupMs) {
    *errorCode = "TARGET_WARMUP";
    return SensorState::kWarmup;
  }
  *errorCode = nullptr;
  return SensorState::kValid;
}

const char* stateName(SensorState state) {
  switch (state) {
    case SensorState::kWarmup: return "WARMUP";
    case SensorState::kValid: return "VALID";
    case SensorState::kFault: return "FAULT";
    default: return "UNKNOWN";
  }
}

void emitTelemetry(uint32_t now) {
  const char* errorCode = nullptr;
  const SensorState state = sensorState(now, &errorCode);
  const bool communicationOk = state != SensorState::kFault;
  const bool breathRawValid =
      std::isfinite(breathRaw) && breathRaw > 0.0F &&
      fresh(breathUpdatedMs, kVitalMaxAgeMs, now);
  const bool heartRawValid =
      std::isfinite(heartRaw) && heartRaw > 0.0F &&
      fresh(heartUpdatedMs, kVitalMaxAgeMs, now);

  Serial.printf(
      "{\"schema_version\":\"%s\",\"device_id\":\"%s\","
      "\"seq\":%lu,\"ts_monotonic_ms\":%lu,"
      "\"uart_frame_ok\":%s,\"checksum_ok\":%s,"
      "\"uart_frames_total\":%lu,\"checksum_errors\":%lu,"
      "\"parse_errors\":%lu,\"consecutive_uart_errors\":%u,"
      "\"human_detected_raw\":",
      kSchemaVersion, kDeviceId, static_cast<unsigned long>(sequence++),
      static_cast<unsigned long>(now), communicationOk ? "true" : "false",
      communicationOk ? "true" : "false", static_cast<unsigned long>(validFrames),
      static_cast<unsigned long>(checksumErrors),
      static_cast<unsigned long>(parseErrors), consecutiveUartErrors);
  printNullableBool(presenceKnown, presenceRaw);
  Serial.print(",\"human_detected_stable\":");
  printNullableBool(presenceStableKnown, presenceStable);
  Serial.print(",\"presence_age_ms\":");
  printAge(presenceKnown, presenceUpdatedMs, now);
  Serial.print(",\"distance_cm_raw\":");
  printNullableFloat(distanceRaw);
  Serial.print(",\"distance_age_ms\":");
  printAge(std::isfinite(distanceRaw), distanceUpdatedMs, now);
  Serial.print(",\"breath_rate_raw\":");
  printNullableFloat(breathRaw);
  Serial.print(",\"breath_rate_filtered\":null,\"breath_raw_valid\":");
  Serial.print(breathRawValid ? "true" : "false");
  Serial.print(",\"breath_age_ms\":");
  printAge(std::isfinite(breathRaw), breathUpdatedMs, now);
  Serial.print(",\"heart_rate_raw\":");
  printNullableFloat(heartRaw);
  Serial.print(",\"heart_raw_valid\":");
  Serial.print(heartRawValid ? "true" : "false");
  Serial.print(",\"heart_verified\":false,\"heart_age_ms\":");
  printAge(std::isfinite(heartRaw), heartUpdatedMs, now);
  Serial.print(",\"total_phase\":");
  printNullableFloat(totalPhase);
  Serial.print(",\"breath_phase\":");
  printNullableFloat(breathPhase);
  Serial.print(",\"heart_phase\":");
  printNullableFloat(heartPhase);
  Serial.print(",\"phase_age_ms\":");
  printAge(std::isfinite(totalPhase), phasesUpdatedMs, now);
  Serial.printf(",\"firmware_version\":\"%s\",\"sensor_firmware_version\":",
                kEspFirmwareVersion);
  if (firmwareKnown) Serial.printf("\"0x%08lX\"", static_cast<unsigned long>(firmwareRaw));
  else Serial.print("null");
  Serial.printf(",\"config_hash\":\"%s\",\"sensor_state\":\"%s\",\"error_code\":",
                kConfigSha256, stateName(state));
  if (errorCode) Serial.printf("\"%s\"", errorCode);
  else Serial.print("null");
  Serial.println("}");
}

bool handleValidFrame(uint16_t type, const uint8_t* data, size_t dataLength,
                      uint32_t now) {
  switch (type) {
    case kTypePhases: {
      if (dataLength < 12) return false;
      const float total = readFloat(data);
      const float breath = readFloat(data + 4);
      const float heart = readFloat(data + 8);
      if (!std::isfinite(total) || !std::isfinite(breath) || !std::isfinite(heart)) return false;
      totalPhase = total;
      breathPhase = breath;
      heartPhase = heart;
      phasesUpdatedMs = now;
      return true;
    }
    case kTypeBreath: {
      if (dataLength < 4) return false;
      breathRaw = readFloat(data);
      if (!std::isfinite(breathRaw)) breathRaw = NAN;
      breathUpdatedMs = now;
      return true;
    }
    case kTypeHeart: {
      if (dataLength < 4) return false;
      heartRaw = readFloat(data);
      if (!std::isfinite(heartRaw)) heartRaw = NAN;
      heartUpdatedMs = now;
      return true;
    }
    case kTypeDistance:
      if (dataLength < 8) return false;
      distanceRaw = readU32(data) ? readFloat(data + 4) : NAN;
      if (!std::isfinite(distanceRaw)) distanceRaw = NAN;
      distanceUpdatedMs = now;
      return true;
    case kTypePresence:
      if (dataLength < 1) return false;
      presenceKnown = true;
      presenceRaw = data[0] != 0;
      presenceUpdatedMs = now;
      updateStablePresence(presenceRaw, now);
      return true;
    case kTypeFirmware:
      if (dataLength < 4) return false;
      firmwareRaw = readU32(data);
      firmwareKnown = true;
      return true;
    default:
      return true;
  }
}

void processFrame(uint32_t now) {
  const size_t dataLength = (static_cast<size_t>(frameBuffer[3]) << 8) |
                            static_cast<size_t>(frameBuffer[4]);
  const bool headerOk = checksum(frameBuffer, 7) == frameBuffer[7];
  const bool dataOk = checksum(frameBuffer + kHeaderSize, dataLength) ==
                      frameBuffer[kHeaderSize + dataLength];
  if (!headerOk || !dataOk) {
    ++checksumErrors;
    recordUartError();
    return;
  }
  const uint16_t type = (static_cast<uint16_t>(frameBuffer[5]) << 8) |
                        frameBuffer[6];
  if (!handleValidFrame(type, frameBuffer + kHeaderSize, dataLength, now)) {
    ++parseErrors;
    recordUartError();
    return;
  }
  recordValidFrame(now);
}

void resetParserWithError() {
  ++parseErrors;
  recordUartError();
  frameLength = 0;
  expectedLength = 0;
}

void consumeByte(uint8_t value, uint32_t now) {
  if (frameLength == 0) {
    if (value == kSof) frameBuffer[frameLength++] = value;
    return;
  }
  if (frameLength >= kMaxFrameSize) {
    resetParserWithError();
    return;
  }
  frameBuffer[frameLength++] = value;
  if (frameLength == kHeaderSize) {
    const size_t dataLength = (static_cast<size_t>(frameBuffer[3]) << 8) |
                              frameBuffer[4];
    if (dataLength > kMaxDataSize) {
      resetParserWithError();
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
  Serial.printf(
      "{\"event\":\"boot\",\"board\":\"esp-wroom-32\","
      "\"firmware_version\":\"%s\",\"config_hash\":\"%s\","
      "\"radar_uart\":\"UART2\",\"rx_gpio\":%d,\"tx_gpio\":%d,"
      "\"baud\":%lu}\n",
      kEspFirmwareVersion, kConfigSha256, kRadarRxPin, kRadarTxPin,
      static_cast<unsigned long>(kRadarBaud));
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
