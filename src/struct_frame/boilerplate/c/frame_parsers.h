/* Struct-frame boilerplate: frame parser main header */

#pragma once

/* Base utilities */
#include "frame_base.h"

/* Frame headers - Start byte patterns and header types */
#include "frame_headers/base.h"
#include "frame_headers/header_basic.h"
#include "frame_headers/header_mavlink_v1.h"
#include "frame_headers/header_mavlink_v2.h"
#include "frame_headers/header_none.h"
#include "frame_headers/header_tiny.h"
#include "frame_headers/header_ubx.h"

/* Payload types - Message structure definitions */
#include "payload_types/base.h"
#include "payload_types/payload_default.h"
#include "payload_types/payload_extended.h"
#include "payload_types/payload_extended_length.h"
#include "payload_types/payload_extended_msg_ids.h"
#include "payload_types/payload_extended_multi_system_stream.h"
#include "payload_types/payload_minimal.h"
#include "payload_types/payload_multi_system_stream.h"
#include "payload_types/payload_seq.h"
#include "payload_types/payload_sys_comp.h"

/* Frame profiles - Pre-defined Header + Payload combinations */
#include "frame_profiles.h"
