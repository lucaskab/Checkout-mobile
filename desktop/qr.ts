// A small QR code encoder (byte mode, error correction level M, versions 1–10: up to 213 bytes) for the invite link on
// the Amigos page. The page sends the modules as text ("1" dark, "0" light, rows joined) and Unity draws them
// (CheckoutDesktopCard). Same steps as the standard (ISO/IEC 18004) and as Project Nayuki's reference encoder:
// data bits → Reed–Solomon blocks → interleave → function patterns → zigzag placement → the mask with the lowest
// penalty → format and version bits. Checked against that encoder in desktop/qr.test.mjs.

const ECC_PER_BLOCK_M = [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26];
const BLOCKS_M = [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5];
const FORMAT_M = 0;

function rawDataModules(version: number) {
	let result = (16 * version + 128) * version + 64;
	if (version >= 2) {
		const align = Math.floor(version / 7) + 2;
		result -= (25 * align - 10) * align - 55;
		if (version >= 7) result -= 36;
	}
	return result;
}
const dataCodewords = (version: number) => Math.floor(rawDataModules(version) / 8) - ECC_PER_BLOCK_M[version] * BLOCKS_M[version];

function gfMultiply(x: number, y: number) {
	let z = 0;
	for (let i = 7; i >= 0; i--) {
		z = (z << 1) ^ ((z >>> 7) * 0x11d);
		z ^= ((y >>> i) & 1) * x;
	}
	return z & 0xff;
}
function rsDivisor(degree: number) {
	const result = new Array<number>(degree).fill(0);
	result[degree - 1] = 1;
	let root = 1;
	for (let i = 0; i < degree; i++) {
		for (let j = 0; j < result.length; j++) {
			result[j] = gfMultiply(result[j], root);
			if (j + 1 < result.length) result[j] ^= result[j + 1];
		}
		root = gfMultiply(root, 0x02);
	}
	return result;
}
function rsRemainder(data: number[], divisor: number[]) {
	const result = new Array<number>(divisor.length).fill(0);
	for (const b of data) {
		const factor = b ^ (result.shift() as number);
		result.push(0);
		divisor.forEach((coef, i) => {
			result[i] ^= gfMultiply(coef, factor);
		});
	}
	return result;
}

function alignmentPositions(version: number, size: number) {
	if (version === 1) return [];
	const count = Math.floor(version / 7) + 2;
	const step = Math.ceil((version * 4 + 4) / (count * 2 - 2)) * 2;
	const result = [6];
	for (let pos = size - 7; result.length < count; pos -= step) result.splice(1, 0, pos);
	return result;
}

/** The QR code of `text` (UTF-8): rows of booleans, true = dark. Null when it does not fit in version 10. */
export function encodeQr(text: string, forcedMask = -1): boolean[][] | null {
	const bytes = Array.from(new TextEncoder().encode(text));
	let version = 1;
	for (; version <= 10; version++) {
		const countBits = version < 10 ? 8 : 16;
		if (4 + countBits + bytes.length * 8 <= dataCodewords(version) * 8) break;
	}
	if (version > 10) return null;
	const capacity = dataCodewords(version) * 8;
	const bits: number[] = [];
	const append = (value: number, length: number) => {
		for (let i = length - 1; i >= 0; i--) bits.push((value >>> i) & 1);
	};
	append(0b0100, 4);
	append(bytes.length, version < 10 ? 8 : 16);
	for (const b of bytes) append(b, 8);
	append(0, Math.min(4, capacity - bits.length));
	append(0, (8 - (bits.length % 8)) % 8);
	for (let pad = 0xec; bits.length < capacity; pad ^= 0xec ^ 0x11) append(pad, 8);
	const data: number[] = [];
	for (let i = 0; i < bits.length; i += 8) data.push(bits.slice(i, i + 8).reduce((acc, bit) => (acc << 1) | bit, 0));

	// Error correction blocks, interleaved.
	const blockCount = BLOCKS_M[version];
	const eccLength = ECC_PER_BLOCK_M[version];
	const rawCodewords = Math.floor(rawDataModules(version) / 8);
	const shortBlocks = blockCount - (rawCodewords % blockCount);
	const shortLength = Math.floor(rawCodewords / blockCount);
	const divisor = rsDivisor(eccLength);
	const blocks: number[][] = [];
	for (let i = 0, k = 0; i < blockCount; i++) {
		const chunk = data.slice(k, k + shortLength - eccLength + (i < shortBlocks ? 0 : 1));
		k += chunk.length;
		const ecc = rsRemainder(chunk, divisor);
		if (i < shortBlocks) chunk.push(0);
		blocks.push(chunk.concat(ecc));
	}
	const codewords: number[] = [];
	for (let i = 0; i < blocks[0].length; i++)
		blocks.forEach((block, j) => {
			if (i !== shortLength - eccLength || j >= shortBlocks) codewords.push(block[i]);
		});

	const size = version * 4 + 17;
	const modules = Array.from({ length: size }, () => new Array<boolean>(size).fill(false));
	const fixed = Array.from({ length: size }, () => new Array<boolean>(size).fill(false));
	const set = (x: number, y: number, dark: boolean) => {
		modules[y][x] = dark;
		fixed[y][x] = true;
	};
	for (let i = 0; i < size; i++) {
		set(6, i, i % 2 === 0);
		set(i, 6, i % 2 === 0);
	}
	const finder = (cx: number, cy: number) => {
		for (let dy = -4; dy <= 4; dy++)
			for (let dx = -4; dx <= 4; dx++) {
				const x = cx + dx;
				const y = cy + dy;
				if (x < 0 || x >= size || y < 0 || y >= size) continue;
				const dist = Math.max(Math.abs(dx), Math.abs(dy));
				set(x, y, dist !== 2 && dist !== 4);
			}
	};
	finder(3, 3);
	finder(size - 4, 3);
	finder(3, size - 4);
	const align = alignmentPositions(version, size);
	align.forEach((ay, i) =>
		align.forEach((ax, j) => {
			const last = align.length - 1;
			if ((i === 0 && j === 0) || (i === 0 && j === last) || (i === last && j === 0)) return;
			for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(ax + dx, ay + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
		}),
	);
	const drawFormat = (mask: number) => {
		const value = (FORMAT_M << 3) | mask;
		let rem = value;
		for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
		const formatBits = ((value << 10) | rem) ^ 0x5412;
		const bit = (i: number) => ((formatBits >>> i) & 1) !== 0;
		for (let i = 0; i <= 5; i++) set(8, i, bit(i));
		set(8, 7, bit(6));
		set(8, 8, bit(7));
		set(7, 8, bit(8));
		for (let i = 9; i < 15; i++) set(14 - i, 8, bit(i));
		for (let i = 0; i < 8; i++) set(size - 1 - i, 8, bit(i));
		for (let i = 8; i < 15; i++) set(8, size - 15 + i, bit(i));
		set(8, size - 8, true);
	};
	drawFormat(0);
	if (version >= 7) {
		let rem = version;
		for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
		const versionBits = (version << 12) | rem;
		for (let i = 0; i < 18; i++) {
			const dark = ((versionBits >>> i) & 1) !== 0;
			const a = size - 11 + (i % 3);
			const b = Math.floor(i / 3);
			set(a, b, dark);
			set(b, a, dark);
		}
	}
	// Zigzag placement of the codewords.
	let index = 0;
	for (let right = size - 1; right >= 1; right -= 2) {
		if (right === 6) right = 5;
		for (let vert = 0; vert < size; vert++)
			for (let j = 0; j < 2; j++) {
				const x = right - j;
				const upward = ((right + 1) & 2) === 0;
				const y = upward ? size - 1 - vert : vert;
				if (!fixed[y][x] && index < codewords.length * 8) {
					modules[y][x] = ((codewords[index >>> 3] >>> (7 - (index & 7))) & 1) !== 0;
					index++;
				}
			}
	}

	const applyMask = (mask: number) => {
		for (let y = 0; y < size; y++)
			for (let x = 0; x < size; x++) {
				if (fixed[y][x]) continue;
				const flip =
					mask === 0 ? (x + y) % 2 === 0
					: mask === 1 ? y % 2 === 0
					: mask === 2 ? x % 3 === 0
					: mask === 3 ? (x + y) % 3 === 0
					: mask === 4 ? (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0
					: mask === 5 ? ((x * y) % 2) + ((x * y) % 3) === 0
					: mask === 6 ? (((x * y) % 2) + ((x * y) % 3)) % 2 === 0
					: (((x + y) % 2) + ((x * y) % 3)) % 2 === 0;
				if (flip) modules[y][x] = !modules[y][x];
			}
	};
	const penalty = () => {
		let result = 0;
		const addHistory = (run: number, history: number[]) => {
			if (history[0] === 0) run += size;
			history.pop();
			history.unshift(run);
		};
		const countPatterns = (h: number[]) => {
			const n = h[1];
			const core = n > 0 && h[2] === n && h[3] === n * 3 && h[4] === n && h[5] === n;
			return (core && h[0] >= n * 4 && h[6] >= n ? 1 : 0) + (core && h[6] >= n * 4 && h[0] >= n ? 1 : 0);
		};
		const terminate = (color: boolean, run: number, history: number[]) => {
			if (color) {
				addHistory(run, history);
				run = 0;
			}
			run += size;
			addHistory(run, history);
			return countPatterns(history);
		};
		const line = (get: (a: number, b: number) => boolean) => {
			for (let a = 0; a < size; a++) {
				let color = false;
				let run = 0;
				const history = [0, 0, 0, 0, 0, 0, 0];
				for (let b = 0; b < size; b++) {
					if (get(a, b) === color) {
						run++;
						if (run === 5) result += 3;
						else if (run > 5) result++;
					} else {
						addHistory(run, history);
						if (!color) result += countPatterns(history) * 40;
						color = get(a, b);
						run = 1;
					}
				}
				result += terminate(color, run, history) * 40;
			}
		};
		line((y, x) => modules[y][x]);
		line((x, y) => modules[y][x]);
		for (let y = 0; y < size - 1; y++)
			for (let x = 0; x < size - 1; x++) {
				const c = modules[y][x];
				if (c === modules[y][x + 1] && c === modules[y + 1][x] && c === modules[y + 1][x + 1]) result += 3;
			}
		const dark = modules.reduce((sum, row) => sum + row.filter(Boolean).length, 0);
		const total = size * size;
		const k = Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1;
		return result + k * 10;
	};
	let mask = forcedMask;
	if (mask < 0) {
		let best = Infinity;
		for (let m = 0; m < 8; m++) {
			applyMask(m);
			drawFormat(m);
			const score = penalty();
			if (score < best) {
				best = score;
				mask = m;
			}
			applyMask(m);
		}
	}
	applyMask(mask);
	drawFormat(mask);
	return modules;
}

/** The modules as one text for Unity: "<size>:" then the rows of "1" / "0". "" when the text does not fit. */
export function qrText(text: string) {
	const modules = encodeQr(text);
	if (!modules) return "";
	return `${modules.length}:${modules.map((row) => row.map((dark) => (dark ? "1" : "0")).join("")).join("")}`;
}
