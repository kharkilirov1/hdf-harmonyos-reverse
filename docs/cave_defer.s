	.text
	.global cave
cave:
	sub	sp, sp, #96
	stp	x0, x1, [sp, #0]
	stp	x2, x3, [sp, #16]
	stp	x4, x5, [sp, #32]
	stp	x6, x7, [sp, #48]
	str	x8, [sp, #64]
	ldr	w10, [x20, #8]
	mov	w11, #401
	cmp	w10, w11
	b.ne	skip
	mov	w11, #8250
	cmp	w19, w11
	b.ne	skip
	ldr	x9, [x20, #0x178]
	cbz	x9, skip
	str	x9, [sp, #80]
	add	x1, sp, #80
	mov	x0, x20
	bl	publish
	add	x0, sp, #72
	mov	x1, #0
	adr	x2, tramp
	mov	x3, x20
	bl	pthread_create
skip:
	ldp	x0, x1, [sp, #0]
	ldp	x2, x3, [sp, #16]
	ldp	x4, x5, [sp, #32]
	ldp	x6, x7, [sp, #48]
	ldr	x8, [sp, #64]
	add	sp, sp, #96
	ldr	w2, [x20, #8]
	mov	w1, w19
	b	back

tramp:
	sub	sp, sp, #48
	stp	x29, x30, [sp, #0]
	stp	x19, x20, [sp, #16]
	str	x21, [sp, #32]
	mov	x19, x0
	mov	w0, #0x8480
	movk	w0, #0x1e, lsl #16
	bl	usleep
	mov	x0, x19
	bl	start
	ldp	x29, x30, [sp, #0]
	ldp	x19, x20, [sp, #16]
	ldr	x21, [sp, #32]
	add	sp, sp, #48
	ret
