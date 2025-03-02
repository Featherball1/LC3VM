#pragma once

#pragma warning(disable:4996)

#include <stdio.h>
#include <stdint.h>
#include <signal.h>

/* windows only */
#include <Windows.h>
#include <conio.h>  // _kbhit

#include "utils.h"

namespace LC3VM {
	// Hardware data for the VM

	extern int running;

	// Memory
	extern const int MEMORY_MAX;			// Max amount of memory locations
	extern uint16_t memory[65536];				// Memory locations store 16-bit values

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
	extern uint16_t reg[R_COUNT];

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

	uint16_t swap16(uint16_t x);

	void read_image_file(FILE* file);

	int read_image(const char* image_path);

	// Memory reading / writing

	void mem_write(uint16_t address, uint16_t val);

	uint16_t mem_read(uint16_t address);

	// Helper functions for implementing the opcodes

	/*
	* Sign extension and condition flags
	*/

	uint16_t sign_extend(uint16_t x, int bit_count);
	void update_flags(uint16_t r);

	// Implementations of standard opcodes
	void op_add(uint16_t instr);
	void op_and(uint16_t instr);
	void op_not(uint16_t instr);
	void op_br(uint16_t instr);
	void op_jmp(uint16_t instr);
	void op_jsr(uint16_t instr);
	void op_ld(uint16_t instr);
	void op_ldi(uint16_t instr);
	void op_ldr(uint16_t instr);
	void op_lea(uint16_t instr);
	void op_st(uint16_t instr);
	void op_sti(uint16_t instr);
	void op_str(uint16_t instr);
	void op_trap(uint16_t instr);
	void op_res(uint16_t instr);
	void op_rti(uint16_t instr);

	void switch_op(uint16_t instr); 

	void run();
}