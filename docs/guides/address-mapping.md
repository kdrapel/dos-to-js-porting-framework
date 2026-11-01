# Guide: DOS Memory Models & Coordinate Mapping

Accurately mapping guest memory coordinates is the single most critical foundation of the port. If your coordinate conversions are off by even a few bytes, disassembler lookups will point to data instead of code, stack frames will be corrupted, and offline execution will fail.

---

## 1. The Four Coordinate Spaces

When analyzing a DOS demo, you will encounter four distinct address spaces:

1. **Capture Memory File Offset (`file_offset`)**:
   The 0-indexed byte offset inside the exported raw `.bin` memory dump (e.g. `memory_main.bin`).
2. **Segment Selector Offset (`reg_offset`)**:
   The value in CPU registers (EIP, ESP, ESI, EDI) and assembly operand displacements (e.g., `mov eax, [0x000469C]`).
3. **Guest Linear Address (`linear_addr`)**:
   The address computed by the CPU's segmentation unit:
   $$\text{linear} = \text{segment.base} + \text{reg\_offset}$$
4. **Disassembler / IDA Address (`ida_addr`)**:
   The coordinate system chosen by the analyst when loading the dump into IDA Pro.

---

## 2. Protected Mode & DOS Extenders

Most 1990s 32-bit DOS demos ran under a DOS extender (DOS/4GW, PMODE/W, CauseWay, or custom extenders like Tran's PMODE).

### The "Flat Model" Trap
In modern operating systems, segment bases are zero. In DOS extenders, segment bases are **often non-zero**:
- An extender may set `CS.base = DS.base = ES.base = SS.base = 0x0000B9C0` (or `0x00010000`).
- If `segment.base = 0xB9C0`, then when `EIP = 0x2C88F`, the CPU actually fetches code from linear address:
  $$0x0000B9C0 + 0x0002C88F = 0x0003824F$$
- If your memory dump was exported starting at linear `0x0000B9C0`, then:
  $$\text{file\_offset} = \text{linear} - 0x0000B9C0 = 0x0002C88F$$
  In this specific case, `file_offset` happens to equal `reg_offset`.
- However, if the dump was exported starting at linear `0x00000000`, then:
  $$\text{file\_offset} = \text{linear} = 0x0003824F \neq 0x0002C88F$$

### Special Segment Overrides (FS and GS)
While CS/DS/ES/SS are usually bound to the application's heap/code base, extenders frequently configure **FS or GS with a base of 0**:
- This allows the 32-bit application to access real-mode low memory using segment override prefixes:
  ```nasm
  mov eax, gs:[0x46C]   ; Read BIOS Timer Tick Counter at 0040:006C
  mov edx, gs:[0x20]    ; Read Real Mode Interrupt Vector 8
  ```
- If your memory dump only covers high memory (e.g., starting at `0xB9C0`), any access through `gs:[...]` will refer to linear addresses below your dump and must be explicitly handled or contracted.

---

## 3. How to Prove Your Coordinate Mapping

Never assume an address formula. Prove it with this step-by-step audit:

1. **GDT (Global Descriptor Table) Verification**:
   - Locate GDTR in `machine_state.json` (e.g., base `0xB9F0`, limit `0x67`).
   - Calculate candidate file offset for GDTR.
   - Inspect raw descriptor entries (8 bytes each: base, limit, type, privilege).
   - Verify that the decoded base and limit in the descriptors match the values in `machine_state.json`.
2. **Instruction Fetch Alignment**:
   - Take the captured CS:EIP from `registers.json`.
   - Calculate candidate file offset.
   - Read 16 bytes from that offset and disassemble them.
   - Verify that the first instruction matches the program's expected execution point (e.g., a known loop or call).
3. **Stack Return Address Anchor**:
   - Inspect the dword at `SS:ESP`.
   - In standard near calls, this is the return address (`EIP + instruction_length`).
   - Check the code 5 bytes before that address: it should be a `call` instruction targeting your current routine!

---

## 4. Common Pitfalls & Traps

- **Wrapped Memory Dumps**: Some capture tools export 8 MB by repeatedly dumping the same 64 KB segment. Always compute a checksum across 64 KB blocks to detect wrapping.
- **Paging**: Check CR0 bit 31. If paging is enabled, linear addresses are translated through page tables to physical memory. In almost all DOS demos from 1993–1998, paging was disabled (CR0 bit 31 = 0), meaning linear equals physical.
- **IDA Rebasing**: If IDA was rebased when creating the project, remember to offset all addresses when cross-referencing between IDA and the runtime binary.
