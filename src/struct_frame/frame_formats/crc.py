"""
CRC calculation utilities for frame formats.

Provides CRC-16-CCITT implementation used by struct-frame payloads.
"""


def calculate_crc16(data: bytes) -> int:
    """
    Calculate CRC-16-CCITT checksum for data.
    
    Polynomial: 0x1021 (x^16 + x^12 + x^5 + 1)
    Initial value: 0xFFFF
    
    Args:
        data: Bytes to calculate CRC for
        
    Returns:
        16-bit CRC value
    """
    crc = 0xFFFF
    
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    
    return crc


def crc_to_bytes(crc: int) -> tuple:
    """
    Convert 16-bit CRC to two bytes.
    
    Args:
        crc: 16-bit CRC value
        
    Returns:
        Tuple of (crc_byte1, crc_byte2) in little-endian order
    """
    crc_byte1 = crc & 0xFF
    crc_byte2 = (crc >> 8) & 0xFF
    return (crc_byte1, crc_byte2)


def bytes_to_crc(crc_byte1: int, crc_byte2: int) -> int:
    """
    Convert two bytes to 16-bit CRC value.
    
    Args:
        crc_byte1: Low byte of CRC
        crc_byte2: High byte of CRC
        
    Returns:
        16-bit CRC value
    """
    return crc_byte1 | (crc_byte2 << 8)


def verify_crc(data: bytes, expected_crc: int) -> bool:
    """
    Verify CRC checksum matches expected value.
    
    Args:
        data: Data to verify
        expected_crc: Expected CRC value
        
    Returns:
        True if CRC matches, False otherwise
    """
    calculated_crc = calculate_crc16(data)
    return calculated_crc == expected_crc
