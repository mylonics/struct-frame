/* Struct-frame boilerplate: frame parser main header */

#pragma once

/* Base utilities */
#include "frame_base.h"

/* Frame headers - Start byte patterns and header types */
#include "frame_headers.h"

/* Payload types - Message structure definitions */
#include "payload_types.h"

/* Frame profiles - Pre-defined Header + Payload combinations, BufferReader/Writer, AccumulatingReader */
#include "frame_profiles.h"
