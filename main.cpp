#pragma warning(disable:4996)
#include <iostream>
#include <stdio.h>
#include <stdint.h>
#include <signal.h>

#include <Windows.h>
#include <conio.h>

#include "utils.h"
#include "LC3VM.h"

int main(int argc, const char* argv[]) {
	// Load arguments
	if (argc < 2) {
		printf("lc3 [image-file1] ...\n");
		exit(2);
	}

	for (int j = 1; j < argc; j++) {
		if (!LC3VM::read_image(argv[j])) {
			printf("failed to load image: %s\n", argv[j]);
			exit(1);
		}
	}

	// Setup - this is a small detail to properly handle input to the terminal
	signal(SIGINT, handle_interrupt);
	disable_input_buffering();

	LC3VM::run(); 

	// Small detail - reset terminal settings at end of program
	restore_input_buffering();

	return 0;
}