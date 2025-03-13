opcodes = {
    "ADD" : 0x1,
    "AND" : 0x5,
    "BR" : 0x0,
    "JMP" : 0xC,
    "JSR" : 0x4,
    "LD" : 0X2,
    "LDI" : 0xA,
    "LDR" : 0x6,
    "LEA" : 0xE,
    "NOT" : 0x9,
    "RET" : 0xC,
    "RTI" : 0x8,
    "ST" : 0x3,
    "STI" : 0xB,
    "STR" : 0x7,
    "TRAP" : 0xF
}

trap_codes = {
    "GETC" : 0x20,
    "OUT" : 0x21,
    "PUTS" : 0x22,
    "IN" : 0x23,
    "PUTSP" : 0x24,
    "HALT" : 0x25,
}

preprocessor_directives = [
    ".ORIG", ".END", ".BLKW", ".FILL", ".STRINGZ"
]

registers = {
    "R0" : 0x0,
    "R1" : 0x1,
    "R3" : 0X2,
    "R4" : 0x3,
    "R5" : 0x4,
    "R6" : 0x5,
    "R7" : 0x6,
    "R_PC" : 0x7,
    "R_COND" : 0x8,
    "R_COUNT" : 0x9,
}

opcodes_trapcodes = list(opcodes.keys()) + list(trap_codes.keys())
asm_keywords = list(opcodes.keys()) + list(trap_codes.keys()) + preprocessor_directives