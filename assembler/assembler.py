import argparse
import os
import array

import keywords
import lc3encodings
import lc3token

"""
The structure of LC3 assembly code

Label:
    - Placed at the beginning of a line
    - Assigns a symbolic name to the address corresponding to the line
Opcode: 
    - reserved symbols corresponding to LC3 instructions
Operands: 
    - Registers - specified by Rn, n being the register number
    - Numbers - indicated by # (decimal), x (hex), b (binary)
    - label - symbolic name of memory location
    - Separated by commas
    - Number, order and type correspond to instruction format
Comment:
    - Anything after a semicolon is a comment, and ignored by the assembler
Assembler directives:
    - Refer to operations used by the assembler, not like the program
    - The opcode for assembler directives begins with a .
Trap codes:
    - Which trap code to execute in the case of a TRAP opcode

The LC3 assembly syntax has the form
    [label] opcode operands [; optional end of line comment]
"""

""" PHASE ONE ASSEMBLY: TOKENISATION AND SCANNING """

def scan(filepath: str, debug: bool = True):
    file = open(filepath)
    symbol_table = {}
    lines_metadata = []
    location_counter = 0x0
    for line_idx, line in enumerate(file):
        tokens = lc3token.tokenize_line(line)

        """CASE 0: The line was empty"""
        if not tokens: continue

        # TODO: check_syntax(tokens)

        """CASE 1: We encounter the program endpoint"""
        if tokens[0].value == ".END":
            if debug: print(f"Line {line_idx} program end point found, exiting scanning")
            lines_metadata.append((tokens, hex(location_counter)))
            break

        """CASE 2: We encounter a label"""
        if tokens[0].token_type == lc3token.TokenType.LABEL:
            if tokens[0].value in symbol_table.keys(): 
                print("ERROR: The label {label} on line {line_idx} was already present in the symbol table (already defined)")
                #return
            symbol_table[tokens[0].value] = location_counter

        """CASE 3: We encounter a preprocessor directive"""
        # Directives that don't accept a label
        if tokens[0].token_type == lc3token.TokenType.ASSEMBLER_DIRECTIVE:
            if tokens[0].value == ".ORIG":
                # .ORIG [address]
                location_counter = int('0' + tokens[1].value, 16)
                print("FOUND PROGRAM ENTRY POINT, SETTING LOCATION COUNTER TO", location_counter)
        # .STRINGZ is a special case, because it takes a label
        elif len(tokens) > 1 and tokens[1].token_type == lc3token.TokenType.ASSEMBLER_DIRECTIVE:
            if tokens[1].value == ".STRINGZ":
                # [label] .STRINGZ [string]
                symbol_table[tokens[0].value] = location_counter
                location_counter = location_counter + len(tokens[2].value) + 1

        """CASE 4: We encounter an opcode"""
        if tokens[0].token_type == lc3token.TokenType.OPCODE:
            location_counter = location_counter + 1

        """CASE 5: We encounter a trapcode"""
        if tokens[0].token_type == lc3token.TokenType.TRAP_CODE:
            location_counter = location_counter + 1

        if debug:  print(f"""
LINE PROCESSING RESULTS
Line {line_idx} split into tokens {tokens}
The location counter is {location_counter}, {hex(location_counter)}
------------------------------------------
        """)
            
        lines_metadata.append((tokens, hex(location_counter)))

    file.close()

    return symbol_table, lines_metadata

"""PHASE TWO ASSEMBLY: ENCODINGS AND GENERATION"""

"""
Encodings
The notation 
... << 12 | ... << 9 | ...
so on, is simply a convenience in python for constructing bit strings. 
Eg NOT is encoded as
1001 | DR | SR | 1 | 11111
In Python we can do this with bit string manipulations
1001 << 12 | DR < 9 | SR < 6 | 0b111111
"""

def generate(symbol_table, lines_metadata, filepath: str, debug: bool = True):
    # Phase 2 of assembling
    CONDS = {
        '.STRINGZ': lambda tokens, data, sym, lc:
        data.fromlist([c for c in tokens[1].value.encode()]) or data.append(0x0),

        **{
            op: lambda toks, data, sym, lc:
            data.append(lc3encodings.encodings[toks[0].value](toks[0].value, sym, lc, toks))
            for op in keywords.opcodes_trapcodes
        }
    }

    data = array.array("H", [])
    data.append(int('0' + lines_metadata[0][0][1].value, 16))

    for tokens, lc in lines_metadata[1:]:

        print("LINE:", tokens, lc)
        if tokens[0].value == '.END':
            break
        print(tokens)

        if tokens[0].token_type != lc3token.TokenType.LABEL:
            CONDS[tokens[0].value](tokens, data, symbol_table, lc)
        elif len(tokens) != 1:
            CONDS[tokens[1].value](tokens[1:], data, symbol_table, lc)

    data.byteswap()
    return data

# Set up the user-facing CLI interface
parser = argparse.ArgumentParser()
parser.add_argument("inputs", metavar = "INPUT", nargs = "*", help = "Input files to assemble")
args = parser.parse_args()

debug = True

for i in args.inputs:
    print("SCANNING")
    symbol_table, lines_metadata = scan(i, debug = debug)
    print("GENERATING")
    data = generate(symbol_table, lines_metadata, i, debug = debug)
    print("GENERATION RESULTS")
    print(data.tobytes().hex())

    file_name = os.path.splitext(i)[0]
    file_name = f'{file_name}-assembled.obj'

    with open(file_name, 'wb') as f:
        f.write(data.tobytes())
    
    print("Saved", file_name)