#include "LC3VM.h"

// Provide definition of the extern global variables defined in header
const int LC3VM::MEMORY_MAX = 65536; 
int LC3VM::running = 0;
uint16_t LC3VM::memory[65536];
uint16_t LC3VM::reg[LC3VM::R_COUNT];

uint16_t LC3VM::swap16(uint16_t x) {
	return (x << 8) | (x >> 8);
}

void LC3VM::read_image_file(FILE* file) {
	uint16_t origin; // Where in memory to place the image
	fread(&origin, sizeof(origin), 1, file);
	origin = swap16(origin);

	uint16_t max_read = LC3VM::MEMORY_MAX - origin;
	uint16_t* p = LC3VM::memory + origin;
	size_t read = fread(p, sizeof(uint16_t), max_read, file);

	// Switch to little endian
	while (read-- > 0) {
		*p = swap16(*p);
		p++;
	}
}

int LC3VM::read_image(const char* image_path) {
	FILE* file = fopen(image_path, "rb");
	if (!file) { return 0; };
	read_image_file(file);
	fclose(file);
	return 1;
}

void LC3VM::mem_write(uint16_t address, uint16_t val) {
	LC3VM::memory[address] = val;
}

uint16_t LC3VM::mem_read(uint16_t address) {
	// A special case is needed for the memory mapped registers
	if (address == LC3VM::MR_KBSR) {
		if (check_key()) {
			LC3VM::memory[LC3VM::MR_KBSR] = (1 << 15);
			LC3VM::memory[LC3VM::MR_KBDR] = getchar();
		}
		else {
			LC3VM::memory[LC3VM::MR_KBSR] = 0;
		}
	}
	return LC3VM::memory[address];
}

uint16_t LC3VM::sign_extend(uint16_t x, int bit_count) {
	if ((x >> (bit_count - 1)) & 1) {
		x |= (0xFFFF << bit_count);
	}
	return x;
}

void LC3VM::update_flags(uint16_t r) {
	if (LC3VM::reg[r] == 0) {
		LC3VM::reg[LC3VM::R_COND] = LC3VM::FL_ZRO;
	}
	else if (LC3VM::reg[r] >> 15) {	// A 1 in the leftmost bit indicates that it is negative
		LC3VM::reg[LC3VM::R_COND] = LC3VM::FL_NEG;
	}
	else {
		LC3VM::reg[LC3VM::R_COND] = LC3VM::FL_POS;
	}
}

void LC3VM::op_add(uint16_t instr) {
	uint16_t r0 = (instr >> 9) & 0x7;					
	uint16_t r1 = (instr >> 6) & 0x7;				
	uint16_t imm_flag = (instr >> 5) & 0x1;			
	if (imm_flag) {
		uint16_t imm5 = sign_extend(instr & 0x1F, 5);
		reg[r0] = reg[r1] + imm5;							
	}
	else {
		uint16_t r2 = instr & 0x7;
		reg[r0] = reg[r1] + reg[r2];					
	}
	update_flags(r0);										
}

void LC3VM::op_and(uint16_t instr) {
	/*
	The binary encoding of AND is basically exactly the same as ADD
	The implementation here is therefore essentially the same as the above, but now replace + by bitwise AND
	*/
	uint16_t r0 = (instr >> 9) & 0x7;					
	uint16_t r1 = (instr >> 6) & 0x7;						
	uint16_t imm_flag = (instr >> 5) & 0x1;				
	if (imm_flag) {
		uint16_t imm5 = sign_extend(instr & 0x1F, 5);
		reg[r0] = reg[r1] & imm5;							
	}
	else {
		uint16_t r2 = instr & 0x7;
		reg[r0] = reg[r1] & reg[r2];					
	}
	update_flags(r0);
}

void LC3VM::op_not(uint16_t instr) {
	/*
	The encoding of NOT is
	15 12  11   9 8  6 5 4    0
	1001      DR   SR  1  1111
	Unlike ADD and AND this only has one source operand.
	*/
	uint16_t r0 = (instr >> 9) & 0x7;					
	uint16_t r1 = (instr >> 6) & 0x7;						
	reg[r0] = ~reg[r1];
	update_flags(r0);
}

void LC3VM::op_br(uint16_t instr) {
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
	uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		
	uint16_t cond_flag = (instr >> 9) & 0x7;			
	if (cond_flag & reg[R_COND]) {						
		reg[R_PC] += pc_offset;					
	}
}

void LC3VM::op_jmp(uint16_t instr) {
	/*
	The encoding of JMP is
	15 12 11  9  8   6   5    0
	1100   000   BaseR   000000

	JMP is an unconditional branch ('jump')
	It sets PC = BaseR
	*/
	uint16_t BaseR = (instr >> 6) & 0x7;				
	reg[R_PC] = reg[BaseR];
}

void LC3VM::op_jsr(uint16_t instr) {
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
	uint16_t flag = (instr >> 11) & 1;				
	reg[R_R7] = reg[R_PC];							
	if (flag == 1) {									
		uint16_t pc_offset = sign_extend(instr & 0x7FF, 11);
		reg[R_PC] += pc_offset;
	}
	else {
		uint16_t BaseR = (instr >> 6) & 0x7;
		reg[R_PC] = reg[BaseR];
	}
}

void LC3VM::op_ld(uint16_t instr) {
	/*
	The encoding of LD is
	15 12 11 9  8         0
	0010   DR    PCoffset9

	LD is a load instruction.
	*/
	uint16_t dr = (instr >> 9) & 0x7;				
	uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		
	reg[dr] = mem_read(reg[R_PC] + pc_offset);
	update_flags(dr);
}

void LC3VM::op_ldi(uint16_t instr) {
	/*
	The encoding of LDI is
	15 12  11 9  8         0
	1010    DR    PCoffset9

	The operation is similar to LD, but instead it addresses memory using an address stored somewhere in memory
	LDI does the operation DR = mem[mem[PC^+ + SEXT(PCoffset9)]]
	as opposed to LD which was DR = mem[PC^+ + SEXT(PCoffset9)]
	*/
	uint16_t r0 = (instr >> 9) & 0x7;						
	uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);	
	reg[r0] = mem_read(mem_read(reg[R_PC] + pc_offset));	
	update_flags(r0);
}

void LC3VM::op_ldr(uint16_t instr) {
	/*
	The encoding of LDR is
	15 12 11 9  8   6   5     0
	0110   DR   BaseR   offset6

	LDR stands for Load Base + offset.
	This differs from the previous LD-type instructions by doing
	DR = mem[BaseR + SEXT(offset6)]
	*/
	uint16_t dr = (instr >> 9) & 0x7;			
	uint16_t r1 = (instr >> 6) & 0x7;					
	uint16_t pc_offset = sign_extend(instr & 0x3F, 6);	
	reg[dr] = mem_read(reg[r1] + pc_offset);
	update_flags(dr);
}

void LC3VM::op_lea(uint16_t instr) {
	/*
	The encoding of LEA is
	15 12  11 9   8         0
	1110    DR     PCoffset9

	LEA is load effective address.
	*/
	uint16_t dr = (instr >> 9) & 0x7;					
	uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);	
	reg[dr] = reg[R_PC] + pc_offset;
	update_flags(dr);
}

void LC3VM::op_st(uint16_t instr) {
	/*
	The encoding of ST is
	15  12  11 9  8         0
	0011    SR     PCoffset9

	ST is store.
	*/
	uint16_t sr = (instr >> 9) & 0x7;				
	uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);		
	mem_write(reg[R_PC] + pc_offset, reg[sr]);
}

void LC3VM::op_sti(uint16_t instr) {
	/*
	The encoding of STI is
	15  12  11 9  8         0
	0011    SR     PCoffset9

	STI is store indirect, similar to the load case.
	*/
	uint16_t sr = (instr >> 9) & 0x7;				
	uint16_t pc_offset = sign_extend(instr & 0x1FF, 9);	
	mem_write(mem_read(reg[R_PC] + pc_offset), reg[sr]);
}

void LC3VM::op_str(uint16_t instr) {
	/*
	The encoding of STR is
	15 12 11 9 8    6   5      0
	0111   SR   BaseR   offset6

	STR is store base + offset, similar to the load case.
	*/
	uint16_t sr = (instr >> 9) & 0x7;			
	uint16_t baser = (instr >> 6) & 0x7;				
	uint16_t pc_offset = sign_extend(instr & 0x3F, 6);	
	mem_write(reg[baser] + pc_offset, reg[sr]);
}

void LC3VM::op_trap(uint16_t instr) {
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

void LC3VM::op_res(uint16_t instr) {}

void LC3VM::op_rti(uint16_t instr) {}

void LC3VM::switch_op(uint16_t instr) {
	uint16_t op = instr >> 12;
	switch (op) {
	case OP_ADD:
		op_add(instr);
		break;
	case OP_AND:
		op_and(instr); 
		break;
	case OP_NOT:
		op_not(instr);
		break;
	case OP_BR:
		op_br(instr);
		break;
	case OP_JMP:
		op_jmp(instr);
		break;
	case OP_JSR:
		op_jsr(instr);
		break;
	case OP_LD:
		op_ld(instr);
		break;
	case OP_LDI:
		op_ldi(instr);
		break;
	case OP_LDR:
		op_ldr(instr);
		break;
	case OP_LEA:
		op_lea(instr);
		break;
	case OP_ST:
		op_st(instr);
		break;
	case OP_STI:
		op_sti(instr);
		break;
	case OP_STR:
		op_str(instr);
		break;
	case OP_TRAP:
		op_trap(instr);
		break;
	case OP_RES:
		op_res(instr);
		break;
	case OP_RTI:
		op_rti(instr); 
	}
}

void LC3VM::run() {
	reg[R_COND] = FL_ZRO;
	enum { PC_START = 0X3000 };
	reg[R_PC] = PC_START;

	running = 1;

	while (running) {
		uint16_t instr = mem_read(reg[R_PC]++); 
		switch_op(instr); 
	}
}