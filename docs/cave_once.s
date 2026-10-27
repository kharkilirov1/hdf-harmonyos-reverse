	.text
	.global cave
cave:
	sub	sp, sp, #32
	str	x30, [sp, #24]
	ldr	w10, [x20, #8]
	mov	w11, #401
	cmp	w10, w11
	b.ne	skip
	mov	w11, #8250
	cmp	w19, w11
	b.ne	skip
	ldr	x9, [x20, #0x178]
	cbz	x9, skip
	str	x9, [sp, #16]
	add	x1, sp, #16
	mov	x0, x20
	bl	publish
skip:
	ldr	x30, [sp, #24]
	add	sp, sp, #32
	ldr	w2, [x20, #8]
	mov	w1, w19
	b	back
