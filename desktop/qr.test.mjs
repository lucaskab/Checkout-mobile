import { expect, test } from "bun:test";
import { encodeQr, qrText } from "./qr.ts";

// Reference matrices from libqrencode 4.1.1 (level M, auto version), rows as hex. With the same mask our encoder must
// give the very same modules: that checks the data bits, the Reed–Solomon blocks and their interleaving, the function
// patterns, the placement and the format / version bits (version 10 has two block sizes and version information).
const references = [
 {
  "text": "https://checkout-server.lucaslfurini.workers.dev/i/K7Q2MX4P",
  "version": 4,
  "mask": 6,
  "rows": [
   "1fdecc47f",
   "105ddbc41",
   "175cd1f5d",
   "174350b5d",
   "1751bb15d",
   "104079a41",
   "1fd55557f",
   "2f1700",
   "13f249197",
   "13b1e221c",
   "cddbde9f",
   "1ab39a5e5",
   "65ab7263",
   "161ec2220",
   "1b673f94c",
   "214563bd",
   "1b76a67f8",
   "82cef057",
   "254a6aed",
   "c3ae649d",
   "1954a2008",
   "11184f238",
   "14d960e7b",
   "100e4c6e7",
   "19c4717fa",
   "1cbc114",
   "1fdf63354",
   "10578371c",
   "1754793f3",
   "1750f3fab",
   "174d7aab7",
   "104e844b7",
   "1fd109370"
  ]
 },
 {
  "text": "https://checkout-server.lucaslfurini.workers.dev/i/ANA2BC3D",
  "version": 4,
  "mask": 3,
  "rows": [
   "1fd01f27f",
   "105e55f41",
   "1745f165d",
   "175b2075d",
   "174d9885d",
   "1041f7941",
   "1fd55557f",
   "137d400",
   "16e96f84b",
   "5a593e6d",
   "16d4997bb",
   "1b981466b",
   "2706c4b8",
   "a9f4c1ae",
   "d6c1b068",
   "30b37fcc",
   "d5f82edc",
   "187613d9",
   "166abdc36",
   "159de8713",
   "13d99692c",
   "10b33ee49",
   "4d15475f",
   "88df2569",
   "1072aa1f1",
   "17ba31a",
   "1fd60bb50",
   "1053b6b1d",
   "17495dbf7",
   "175279c25",
   "1759b1c6c",
   "104d2a739",
   "1fda0da54"
  ]
 },
 {
  "text": "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
  "version": 10,
  "mask": 1,
  "rows": [
   "1fd069155555e7f",
   "1042fb6ddddda41",
   "175f00688888e5d",
   "174c69baaaaaa5d",
   "174a6c1fd55525d",
   "1051f02c5dddc41",
   "1fd55555555557f",
   "3ba9c7777500",
   "146366c7d555425",
   "10433a6aaaaaa7",
   "5cf1f162222125",
   "3033a5b777757a",
   "e5336315555452",
   "1a846336aaaaaa7",
   "34b1f262222125",
   "50f2abb7777579",
   "e5744c15555453",
   "1b881166aaaaaa7",
   "c714962222125",
   "5bb165b777757a",
   "fc24cc15555452",
   "1a811566aaaaaa7",
   "107a15962222125",
   "15bc1e5b777757a",
   "17eb49c15555452",
   "1a871e66aaaaaa7",
   "1f8909fe2221f5",
   "1d1e9e5c777751a",
   "195819cd5555752",
   "1514526c6aaab17",
   "1bfb60d7e2221f5",
   "17be9eddf7777da",
   "1e48597c9555682",
   "c2472c6aaaa8a6",
   "1d53d0916222054",
   "119a1e5df7777d8",
   "18441b8c9555683",
   "9a42066aaaa8a7",
   "18d7c1516222055",
   "109a149df7777da",
   "18cc1c4c9555682",
   "9a52f66aaaa8a7",
   "1d2c3516222055",
   "119f199df7777da",
   "19fa1b4c9555682",
   "9982566aaaa8a7",
   "14c041516222055",
   "1f1c5c9df7777da",
   "7aef4fd5557f2",
   "19d9646aaab17",
   "1fd3f1556222355",
   "104d9c94777751a",
   "174aff87d5555f2",
   "1749296f6aaab74",
   "175f91d96222157",
   "10410cdab7776a8",
   "1fd29e461555621"
  ]
 }
];

const hexRow = (row, size) => BigInt(`0x${row}`).toString(2).padStart(size, "0");

for (const ref of references)
	test(`QR v${ref.version} (${ref.text.length} bytes) matches the reference with mask ${ref.mask}`, () => {
		const size = ref.version * 4 + 17;
		const modules = encodeQr(ref.text, ref.mask);
		expect(modules.length).toBe(size);
		expect(modules.map((row) => row.map((dark) => (dark ? "1" : "0")).join(""))).toEqual(ref.rows.map((row) => hexRow(row, size)));
	});

test("the invite link fits in a version 4 code and goes to Unity as text", () => {
	const text = qrText("https://checkout-server.lucaslfurini.workers.dev/i/K7Q2MX4P");
	expect(text.startsWith("33:")).toBe(true);
	expect(text.length).toBe(3 + 33 * 33);
	expect(qrText("x".repeat(400))).toBe("");
});
