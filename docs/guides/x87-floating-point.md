# Guide: x87 FPU Emulation & Precision Fidelity

In 1990s 3D DOS demos, the x87 floating-point unit handled matrix math, camera transformations, vertex projections, lighting vectors, and spline curves. Emulating x87 behavior in JavaScript requires careful attention to precision, stack management, and rounding.

---

## 1. The x87 FPU Architecture

The x87 coprocessor operates as an 8-register circular stack:
- Registers are designated `ST(0)` (the stack top) through `ST(7)`.
- Operations push values (`FLD`, `FILD`), pop values (`FSTP`, `FISTP`), and compute between stack slots (`FMUL`, `FADD`, `FSUB`, `FDIV`, `FXCH`).
- The **Status Word (SW)** maintains:
  - `TOP` pointer (bits 11–13): points to the current `ST(0)` physical register (0–7).
  - Condition code flags `C0`, `C1`, `C2`, `C3` (used for comparisons and transcendental bounds).
- The **Control Word (CW)** controls:
  - **Precision Control (PC, bits 8–9)**:
    - `00`: 24-bit single precision (float32 mantissa).
    - `10`: 53-bit double precision (float64 mantissa).
    - `11`: 64-bit extended precision (float80 mantissa).
  - **Rounding Control (RC, bits 10–11)**:
    - `00`: Round to nearest or even.
    - `01`: Round down (toward $-\infty$).
    - `10`: Round up (toward $+\infty$).
    - `11`: Truncate (toward 0).

---

## 2. Why JavaScript Math Causes Visual Drift

Standard JavaScript numbers are IEEE 754 double precision (64-bit float, 53-bit significand).
If a demo configured the FPU Control Word to 24-bit precision (common for high-speed graphics in the 1990s):
- `fmul` and `fadd` on the original x87 truncated the result to a 24-bit mantissa after every operation.
- In JavaScript, `a * b` preserves 53 bits of precision.
- A difference of $10^{-7}$ in one frame compounds exponentially over hundreds of matrix multiplications:
  - By frame 300, objects appear slightly rotated or scaled.
  - By frame 1000, 3D vertices drift off-screen or spline paths diverge completely.

### The Precision Solution
During reverse engineering:
1. **Audit the Control Word**: Check what CW values are loaded by `FLDCW` (e.g. `0x007F` for 24-bit nearest, `0x037F` for 64-bit extended, `0x0C7F` for 24-bit truncate).
2. **Explicit Float32 Rounding**: When CW specifies 24-bit mode, use `Math.fround(result)` after every floating-point operation in JavaScript!
   ```javascript
   // Emulating x87 in 24-bit mode:
   let st0 = Math.fround(a * b);
   ```
3. **Exact Dyadic Math for Critical Kernels**: For matrix normalization or ray-casting where 80-bit extended precision is required, use exact BigInt arithmetic (`mantissa * 2^exponent`) to eliminate rounding discrepancies.

---

## 3. Trigonometric Functions (`FSIN`, `FCOS`, `FPATAN`)

The x87 transcendental instructions (`FSIN`, `FCOS`, `FSINCOS`, `FPATAN`) do not produce bit-for-bit identical results to modern JavaScript `Math.sin()` or `Math.cos()`:
- x87 uses polynomial approximations (CORDIC algorithms or Taylor series with internal constant approximations of $\pi$).
- While modern `Math.sin()` is accurate to 53 bits, differences in the lower bits can cause subtle phase shifts.
- If an intro uses precomputed sine tables (lookup tables in memory), reverse-engineer and reuse the exact table rather than calling `Math.sin()`.
- If it uses runtime `FSIN`/`FCOS`, compare the JavaScript `Math.cos()` output against the Unicorn x87 output. Usually, `Math.fround(Math.cos(x))` is sufficient to prevent cumulative drift.

---

## 4. Reverse Subtraction and Operand Order

Notice that x87 assembly instructions like `FSUBRP` perform **reverse subtraction**:
```nasm
fld  dword ptr [u]
fld  dword ptr [v]
fsubrp st(1), st(0)   ; ST(1) = ST(0) - ST(1), then pop
```
This computes $v - u$, **not** $u - v$. A sign inversion in a 3D cross product will invert face normals, causing backface culling to hide visible geometry. Always verify operand ordering against the execution trace.
