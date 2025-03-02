/*
Goal:
	- Create a VM that simulates the LC-3 educational compute rarchitecture

LC-3 has
	- 65536 memory locations which store 16 bit values (total storage 128KB)
	- 10 total 16-bit registers
		- 8 general purpose registers (R0-R7)
		- 1 program counter (PC)
		- 1 condition flags (COND)
	- 16 opcodes
		- Each opcode represents one task that the CPU can do
	- 3 condition flags
		- Condition flags are used for the CPU to signal various situations
		- In LC-3 they indicate the sign of the previous calculation
	- Two memory mapped registers
		- The keyboard status register KBSR and keyboard data register KBDR
		- KBSR indicates whether a key has been pressed
		- KBDR identifies which key was pressed
		- Memory mapped registers are typically used to interact with special hardware devices
		- They are not accessible from the normal register table, and a special address is reserved for them in memory
		- To read and write to these registers, just read and write to their memory location
A tool called an assembler translates each assembly instruction into a 16-bit binary instruction
that the VM can understand. This is our machine code.
*/

#pragma warning(disable:4996)

#include <stdio.h>
#include <stdint.h>
#include <signal.h>
/* windows only */
#include <Windows.h>
#include <conio.h>  // _kbhit

// Small details (not related to VM, can ignore, they are for input buffering on windows)
HANDLE hStdin = INVALID_HANDLE_VALUE;
DWORD fdwMode, fdwOldMode;

void disable_input_buffering() {
	hStdin = GetStdHandle(STD_INPUT_HANDLE);
	GetConsoleMode(hStdin, &fdwOldMode); /* save old mode */
	fdwMode = fdwOldMode
		^ ENABLE_ECHO_INPUT  /* no input echo */
		^ ENABLE_LINE_INPUT; /* return when one or
								more characters are available */
	SetConsoleMode(hStdin, fdwMode); /* set new mode */
	FlushConsoleInputBuffer(hStdin); /* clear buffer */
}

void restore_input_buffering() {
	SetConsoleMode(hStdin, fdwOldMode);
}

uint16_t check_key() {
	return WaitForSingleObject(hStdin, 1000) == WAIT_OBJECT_0 && _kbhit();
}

void handle_interrupt(int signal) {
	restore_input_buffering();
	printf("\n");
	exit(-2);
}

// Hardware data for the VM

// Memory
constexpr int MEMORY_MAX = 65536;			// Max amount of memory locations
uint16_t memory[MEMORY_MAX];				// Memory locations store 16-bit values

// Registers
enum {
	R_R0 = 0,								// General purpose registers
	R_R1,
	R_R2,
	R_R3,
	R_R4,
	R_R5,
	R_R6,
	R_R7,
	R_PC,									// Program counter
	R_COND,									// Condition flags
	R_COUNT
};
uint16_t reg[R_COUNT];

// Opcodes
enum {
	OP_BR = 0,								// Branch
	OP_ADD,									// Add
	OP_LD,									// Load
	OP_ST,									// Store
	OP_JSR,									// Jump register
	OP_AND,									// Bitwise and
	OP_LDR,									// Load register
	OP_STR,									// Store register
	OP_RTI,									// Unused
	OP_NOT,									// Bitwise not
	OP_LDI,									// Load indirect
	OP_STI,									// Store indirect
	OP_JMP,									// Jump
	OP_RES,									// Reserved 
	OP_LEA,									// Load effect address
	OP_TRAP									// Execute trap
};

// Condition flags
enum {
	FL_POS = 1 << 0,						// Positive
	FL_ZRO = 1 << 1,						// Zero
	FL_NEG = 1 << 2,						// Negative
};

// Memory mapped registers
enum {
	MR_KBSR = 0xFE00,						// Keyboard status
	MR_KBDR = 0xFE02,						// Keyboard data
};

// Trap codes
enum {
	TRAP_GETC = 0x20,						// Read single character from keyboard
	TRAP_OUT = 0x21,						// Write a character in R0[7:0] to console display
	TRAP_PUTS = 0x22,						// Write a string of ASCII characters to console display
	TRAP_IN = 0x23,							// Print a prompt on screen and read single keyboard character
	TRAP_PUTSP = 0x24,						// Write string of ASCII characters to console
	TRAP_HALT = 0x25,						// Halt execution and print message to console
};

// Reading LC-3 programs into memory

uint16_t swap16(uint16_t x) {
	return (x << 8) | (x >> 8);
}

void read_image_file(FILE* file) {
	uint16_t origin;						// Where in memory to place the image
	fread(&origin, sizeof(origin), 1, file);
	origin = swap16(origin);

	uint16_t max_read = MEMORY_MAX - origin;
	uint16_t* p = memory + origin;
	size_t read = fread(p, sizeof(uint16_t), max_read, file);

	// Switch to little endian
	while (read-- > 0) {
		*p = swap16(*p);
		p++;
	}
}

int read_image(const char* image_path) {
	FILE* file = fopen(image_path, "rb");
	if (!file) { return 0; };
	read_image_file(file);
	fclose(file);
	return 1;
}

// Memory reading / writing

void mem_write(uint16_t address, uint16_t val) {
	memory[address] = val;
}

uint16_t mem_read(uint16_t address) {
	// A special case is needed for the memory mapped registers
	if (address == MR_KBSR) {
		if (check_key()) {
			memory[MR_KBSR] = (1 << 15);
			memory[MR_KBDR] = getchar();
		}
		else {
			memory[MR_KBSR] = 0;
		}
	}
	return memory[address];
}

// Helper functions for implementing the opcodes

// Sign extension
	// If we need to add numbers with a different amount of bits,
	// We need to extend the smaller-bit number to match the bigger
	// This can cause issues with negative numbers. This function fixes those subtleties
uint16_t sign_extend(uint16_t x, int bit_count) {
	if ((x >> (bit_count - 1)) & 1) {
		x |= (0xFFFF << bit_count);
	}
	return x;
}

// Any time a value is written to the register, we need to update the condition flags
// The condition flags in LC-3 only indicate the sign of the number
void update_flags(uint16_t r) {
	if (reg[r] == 0) {
		reg[R_COND] = FL_ZRO;
	}
	else if (reg[r] >> 15) {				// A 1 in the leftmost bit indicates that it is negative
		reg[R_COND] = FL_NEG;
	}
	else {
		reg[R_COND] = FL_POS;
	}
}

int main(int argc, const char* argv[]) {
	// Load arguments
	if (argc < 2) {
		printf("lc3 [image-file1] ...\n");
		exit(2);
	}

	for (int j = 1; j < argc; j++) {
		if (!read_image(argv[j])) {
			printf("failed to load image: %s\n", argv[j]);
			exit(1);
		}
	}

	// Setup - this is a small detail to properly handle input to the terminal
	signal(SIGINT, handle_interrupt);
	disable_input_buffering();

	reg[R_COND] = FL_ZRO;
	enum { PC_START = 0X3000 };
	reg[R_PC] = PC_START;

	int running = 1;
	while (running) {
		// Fetch
		uint16_t instr = mem_read(reg[R_PC]++);
		uint16_t op = instr >> 12;

		switch (op) {
		case OP_ADD:
		{
			/*
			Binary encodings of opcodes

			For this instruction (not immediate mode), the encoding is
			15 12 11 9  8 6 5  4  3 2   0
			0001   DR   SR1 0   00   SR2

			This is telling you how the 16 binary digits are associated with data in the instruction.
			In add's case above, we need
				- The instruction code (0001)
				- The destination register (where to write output)
				- SR1, the left parameter of the ADD ("source operand")
				- SR2, the right parameter of the ADD ("source operand")
			Note there is another immediate mode instruction for ADD, see documentation.

			The destination register is inside bits 11 to 9
			As such, we need to right shift by 9 places (sending DR to the start of the number)
			and then delete everything that isn't the first three things remaining
			in order to get the address of DR. We can do this by bitwise & with 7 in hexadecimal (111 in binary)

			Similarly we can obtain the binary encodings of r1 and imm_flag
			*/
			uint16_t r0 = (instr >> 9) & 0x7;						// Destination register DR
			uint16_t r1 = (instr >> 6) & 0x7;						// First operand SR1
			uint16_t imm_flag = (instr >> 5) & 0x1;					// Immediate mode flag
			if (imm_flag) {
				uint16_t imm5 = sign_extend(instr & 0x1F, 5);
				reg[r0] = reg[r1] + imm5;							// Write output of calculation to DR
			}
			else {
				uint16_t r2 = instr & 0x7;
				reg[r0] = reg[r1] + reg[r2];						// Write output of calculation to DR
			}
			update_flags(r0);										// Update flags after writing to register
		}
		break;
		case OP_AND:
		{
			/*
			The binary encoding of AND is basically exactly the same as ADD
			The implementation here is therefore essentially the same as the above, but now replace + by bitwise AND
			*/
			uint16_t r0 = (instr >> 9) & 0x7;						// Destination register DR
			uint16_t r1 = (instr >> 6) & 0x7;						// First operand SR1
			uint16_t imm_flag = (instr >> 5) & 0x1;					// Immediate mode flag
			if (imm_flag) {
				uint16_t imm5 = sign_extend(instr & 0x1F, 5);
				reg[r0] = reg[r1] & imm5;							// Write output of calculation to DR
			}
			else {
				uint16_t r2 = instr & 0x7;
				reg[r0] = reg[r1] & reg[r2];						// Write output of calculation to DR
			}
			update_flags(r0);										// Update flags after writing to register
		}
		break;
		case OP_NOT:
		{
			/*
			The encoding of NOT is
			15 12  11   9 8  6 5 4    0
			1001      DR   SR  1  1111
			Unlike ADD and AND this only has one source operand.
			*/
			uint16_t r0 = (instr >> 9) & 0x7;							// Destination register DR
			uint16_t r1 = (instr >> 6) & 0x7;							// First operand SR1
			reg[r0] = ~reg[r1];
			update_flags(r0);
		}
		break;
		case OP_BR:
		{
			/*
			The encoding of BR is
			15  12  11  10   9    8           0
			0000     n   z   p      PCoffset9
			n, z and p stand for each condition code (negative, zero, positive).
			PCoffset9 is telling us to add to the program counter.
			Branch instructions specify condition codes.
			If specified condition codes are set, the branch is taken, by setting the PC to address specified in instruction.
			Ekse, the next instruction is executed (+1 from current PC)
			*/
			uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		// Program counter offset
			uint16_t cond_flag = (instr >> 9) & 0x7;				// Condition flags in BR instruction
			if (cond_flag & reg[R_COND]) {							// Check whether to execute BR
				reg[R_PC] += pc_offset;								// If true, increment PC by offset
			}
		}
		break;
		case OP_JMP:
		{
			/*
			The encoding of JMP is
			15 12 11  9  8   6   5    0
			1100   000   BaseR   000000

			JMP is an unconditional branch ('jump')
			It sets PC = BaseR
			*/
			uint16_t BaseR = (instr >> 6) & 0x7;					// Base register
			reg[R_PC] = reg[BaseR];
		}
		break;
		case OP_JSR:
		{
			/*
			The encoding of JSR is
			15 12 11 10           0
			0100   1    PCoffset11
			The encoding of JSRR is
			15 12 11 10  9 8    6   5      0
			0100   0   00   BaseR    000000

			JSR is jump to subroutine.
			The bit 11 in the instruction tells is a flag to execute JSR or JSRR.
			*/
			uint16_t flag = (instr >> 11) & 1;					// JSR or JSRR flag
			reg[R_R7] = reg[R_PC];									// Incremented PC saved in R7 (see spec)
			if (flag == 1) {										// JSR
				uint16_t pc_offset = sign_extend(instr & 0x7FF, 11);// The PC offset
				reg[R_PC] += pc_offset;
			}
			else {													// JSRR
				uint16_t BaseR = (instr >> 6) & 0x7;
				reg[R_PC] = reg[BaseR];
			}
		}
		break;
		case OP_LD:
		{
			/*
			The encoding of LD is
			15 12 11 9  8         0
			0010   DR    PCoffset9

			LD is a load instruction.
			*/
			uint16_t dr = (instr >> 9) & 0x7;						// Destination register DR
			uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		// Short PC offset used to get memory location
			reg[dr] = mem_read(reg[R_PC] + pc_offset);
			update_flags(dr);
		}
		break;
		case OP_LDI:
		{
			/*
			The encoding of LDI is
			15 12  11 9  8         0
			1010    DR    PCoffset9

			The operation is similar to LD, but instead it addresses memory using an address stored somewhere in memory
			LDI does the operation DR = mem[mem[PC^+ + SEXT(PCoffset9)]]
			as opposed to LD which was DR = mem[PC^+ + SEXT(PCoffset9)]
			*/
			uint16_t r0 = (instr >> 9) & 0x7;						// Destination register	DR
			uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		// PCoffset 9
			reg[r0] = mem_read(mem_read(reg[R_PC] + pc_offset));	// Add pc_offset to current PC, look at that memory location to get final address
			update_flags(r0);										// Update flags after writing to register
		}
		break;
		case OP_LDR:
		{
			/*
			The encoding of LDR is
			15 12 11 9  8   6   5     0
			0110   DR   BaseR   offset6

			LDR stands for Load Base + offset.
			This differs from the previous LD-type instructions by doing
			DR = mem[BaseR + SEXT(offset6)]
			*/
			uint16_t dr = (instr >> 9) & 0x7;						// Destination register DR
			uint16_t r1 = (instr >> 6) & 0x7;						// Base regster
			uint16_t pc_offset = sign_extend(instr & 0x3F, 6);		// Short PC offset used to get memory location
			reg[dr] = mem_read(reg[r1] + pc_offset);
			update_flags(dr);
		}
		break;
		case OP_LEA:
		{
			/*
			The encoding of LEA is
			15 12  11 9   8         0
			1110    DR     PCoffset9

			LEA is load effective address.
			*/
			uint16_t dr = (instr >> 9) & 0x7;						// Destination register DR
			uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		// Short PC offset used to get memory location
			reg[dr] = reg[R_PC] + pc_offset;
			update_flags(dr);
		}
		break;
		case OP_ST:
		{
			/*
			The encoding of ST is
			15  12  11 9  8         0
			0011    SR     PCoffset9

			ST is store.
			*/
			uint16_t sr = (instr >> 9) & 0x7;						// Source register SR
			uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		// Short PC offset used to get memory location
			mem_write(reg[R_PC] + pc_offset, reg[sr]);
		}
		break;
		case OP_STI:
		{
			/*
			The encoding of STI is
			15  12  11 9  8         0
			0011    SR     PCoffset9

			STI is store indirect, similar to the load case.
			*/
			uint16_t sr = (instr >> 9) & 0x7;						// Source register SR
			uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		// Short PC offset used to get memory location
			mem_write(mem_read(reg[R_PC] + pc_offset), reg[sr]);
		}
		break;
		case OP_STR:
		{
			/*
			The encoding of STR is
			15 12 11 9 8    6   5      0
			0111   SR   BaseR   offset6

			STR is store base + offset, similar to the load case.
			*/
			uint16_t sr = (instr >> 9) & 0x7;						// Source register SR
			uint16_t baser = (instr >> 6) & 0x7;					// Base register BR
			uint16_t pc_offset = sign_extend(instr & 0x3F, 6);		// Short PC offset used to get memory location
			mem_write(reg[baser] + pc_offset, reg[sr]);
		}
		break;
		case OP_TRAP:
		{
			/*
			The encoding of TRAP is
			15 12  11   8   7        0
			1111    0000    trapvect8
			*/
			reg[R_R7] = reg[R_PC];

			switch (instr & 0xFF) {
			case TRAP_GETC:
				/* read a single ASCII char */
				reg[R_R0] = (uint16_t)getchar();
				update_flags(R_R0);
				break;
			case TRAP_OUT:
				putc((char)reg[R_R0], stdout);
				fflush(stdout);
				break;
			case TRAP_PUTS:
			{
				/* one char per word */
				uint16_t* c = memory + reg[R_R0];
				while (*c)
				{
					putc((char)*c, stdout);
					++c;
				}
				fflush(stdout);
			}
			break;
			case TRAP_IN:
			{
				printf("Enter a character: ");
				char c = getchar();
				putc(c, stdout);
				fflush(stdout);
				reg[R_R0] = (uint16_t)c;
				update_flags(R_R0);
			}
			break;
			case TRAP_PUTSP:
			{
				/* one char per byte (two bytes per word)
				   here we need to swap back to
				   big endian format */
				uint16_t* c = memory + reg[R_R0];
				while (*c)
				{
					char char1 = (*c) & 0xFF;
					putc(char1, stdout);
					char char2 = (*c) >> 8;
					if (char2) putc(char2, stdout);
					++c;
				}
				fflush(stdout);
			}
			break;
			case TRAP_HALT:
				puts("HALT");
				fflush(stdout);
				running = 0;
				break;
			}
		}
		break;
		case OP_RES:
			break;
		case OP_RTI:
		{
			/*
			The encoding of RTI is
			15  12  11         0
			1000    000000000000

			RTI is return from interrupt.
			*/
			break;
		}
		default:
			// Opcode did not exist
			break;
		}
	}

	// Small detail - reset terminal settings at end of program
	restore_input_buffering();

	return 0;
}