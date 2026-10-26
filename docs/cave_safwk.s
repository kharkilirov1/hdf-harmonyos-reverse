	.text
	.global cave
cave:
	sub	sp, sp, #32
	str	x30, [sp, #24]
	ldr	w10, [x20, #8]
	cmp	w10, #401
	b.ne	skip
	add	x8, sp, #16
	mov	x0, x20
	bl	getter
	add	x1, sp, #16
	mov	x0, x20
	bl	publish
skip:
	ldr	x30, [sp, #24]
	add	sp, sp, #32
	ldr	w2, [x20, #8]
	mov	w1, w19
	b	back
