import keywords
import lc3token

UINT16_MAX = 2 ** 16

def encode_add(opcode, symbol_table, location_counter, tokens):
    if tokens[3].token_type == lc3token.TokenType.REGISTER:
        # Not immediate mode
        return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[1].value] << 6 | keywords.registers[tokens[3].value]
    else:
        # Immediate mode (imm5 flag is now true)
        return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[1].value] << 6 | 1 << 5 | ((UINT16_MAX + tokens[3].value) & 0b11111)

def encode_and(opcode, symbol_table, location_counter, tokens):
    if tokens[3].token_type == lc3token.TokenType.REGISTER:
        # Not immediate mode
        return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[1].value] << 6 | keywords.registers[tokens[3].value]
    else:
        # Immediate mode (imm5 flag is now true)
        return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[1].value] << 6 | 1 << 5 | ((UINT16_MAX + tokens[3].value) & 0b11111)

def encode_not(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[2].value] << 6 | 0b11111

def encode_br(opcode, symbol_table, location_counter, tokens):
    if tokens[0].v == 'BR':
        op |= 1 << 11
        op |= 1 << 10
        op |= 1 << 9
    if 'n' in tokens[0].v:
        op |= 1 << 11
    if 'z' in tokens[0].v:
        op |= 1 << 10
    if 'p' in tokens[0].v:
        op |= 1 << 9

    if tokens[1].token_type == lc3token.TokenType.LABEL:
        pcoffset9 = ((symbol_table[tokens[1].v] - location_counter) & 0b111111111)
    elif tokens[1].token_type == lc3token.TokenType.CONST:
        pcoffset9 = tokens[1].v & 0b111111111
    else:
        raise Exception()

    return op | pcoffset9

def encode_jmp(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | 0b000 << 9 | keywords.registers[tokens[1].value] << 6 | 0b000000

def encode_jsr(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | 1 << 11 | (symbol_table[tokens[1].value] - location_counter) & 0b11111111111

def encode_ld(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) &0b111111111

def encode_ldi(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) &0b111111111

def encode_ldr(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[2].value] << 6 | ((UINT16_MAX + tokens[3].value) & 0b111111)

def encode_lea(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) & 0b11111111

def encode_st(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) &0b111111111

def encode_sti(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) &0b111111111

def encode_str(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes[opcode] << 12 | keywords.registers[tokens[1].value] << 9 | keywords.registers[tokens[2].value] << 6 | ((UINT16_MAX + tokens[3].value) & 0b111111)

def encode_trap(opcode, symbol_table, location_counter, tokens):
    return keywords.opcodes["TRAP"] << 12 | keywords.trap_codes[tokens[0].value]

def encode_rti(opcode, symbol_table, location_counter, tokens):
    return 0b1000000000000000

encodings = {
    'ADD' : lambda opcode, symbol_table, location_counter, tokens: encode_add(opcode, symbol_table, location_counter, tokens),
    'AND' : lambda opcode, symbol_table, location_counter, tokens: encode_and(opcode, symbol_table, location_counter, tokens),
    'NOT' : lambda opcode, symbol_table, location_counter, tokens: encode_not(opcode, symbol_table, location_counter, tokens),
    'BR' : lambda opcode, symbol_table, location_counter, tokens: encode_br(opcode, symbol_table, location_counter, tokens),
    'JMP' : lambda opcode, symbol_table, location_counter, tokens: encode_jmp(opcode, symbol_table, location_counter, tokens),
    'JSR' : lambda opcode, symbol_table, location_counter, tokens: encode_jsr(opcode, symbol_table, location_counter, tokens),
    'LD' : lambda opcode, symbol_table, location_counter, tokens: encode_ld(opcode, symbol_table, location_counter, tokens),
    'LDI' : lambda opcode, symbol_table, location_counter, tokens: encode_ldi(opcode, symbol_table, location_counter, tokens),
    'LDR' : lambda opcode, symbol_table, location_counter, tokens: encode_ldr(opcode, symbol_table, location_counter, tokens),
    'LEA' : lambda opcode, symbol_table, location_counter, tokens: encode_lea(opcode, symbol_table, location_counter, tokens),
    'ST' : lambda opcode, symbol_table, location_counter, tokens: encode_st(opcode, symbol_table, location_counter, tokens),
    'STI' : lambda opcode, symbol_table, location_counter, tokens: encode_sti(opcode, symbol_table, location_counter, tokens),
    'STR' : lambda opcode, symbol_table, location_counter, tokens: encode_str(opcode, symbol_table, location_counter, tokens),
    'TRAP' : lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'RTI' : lambda opcode, symbol_table, location_counter, tokens: encode_rti(opcode, symbol_table, location_counter, tokens),

    'GETC': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'OUT': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'PUTS': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'IN': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'PUTSP': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'HALT': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
}