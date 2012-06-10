#!/usr/bin/python
# extract readme from source code
# code by Albert Zeyer, www.az2000.de, 2012-06-10
# code under BSD

def extract(ins, out):
	state = 0
	outstate = 0
	while True:
		c = ins.read(1)
		if not c: break
		if state == 0:
			if c == "#":
				if outstate == 1:
					out.write("\n")
				state = 1
				outstate = 0
				continue
			outstate = 1
			if c == "\n": continue
			state = 10
		if state == 1:
			if c == " ":
				state = 2
				continue
			state = 2
		if state == 2:
			out.write(c)
			if c == "\n":
				state = 0
			continue
		if state == 10:
			if c == "\n":
				state = 0

if __name__ == '__main__':
	extract(open("binstruct.py"), open("README.md", "w"))
	