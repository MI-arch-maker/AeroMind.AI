#pragma once

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace aeromind::sitl {

struct SimFrame {
  std::uint8_t message_id{};
  std::vector<std::uint8_t> payload;
  std::uint8_t sequence{};
  std::uint8_t system_id{1};
  std::uint8_t component_id{1};
};

class MavlinkLikeCodec {
 public:
  static std::vector<std::uint8_t> encode(const SimFrame& frame);
  static SimFrame decode(const std::vector<std::uint8_t>& bytes);
};

class ExternalControlPort {
 public:
  virtual ~ExternalControlPort() = default;
  virtual void set_attitude(float roll_deg, float pitch_deg, float yaw_deg, float thrust) = 0;
  virtual void set_position(double latitude, double longitude, float altitude_m) = 0;
};

class VirtualHal {
 public:
  virtual ~VirtualHal() = default;
  virtual float roll() const = 0;
  virtual float pitch() const = 0;
  virtual float yaw() const = 0;
  virtual float throttle() const = 0;
};

}  // namespace aeromind::sitl
