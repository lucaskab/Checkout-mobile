import { describe, expect, test } from "bun:test";
import { getCurrentShelf } from "./shelf-selection";

describe("getCurrentShelf", () => {
	test("reads the latest assignment when a cached press handler is called", () => {
		let assignments = { produce: 1 };
		const handleShelfPress = () =>
			getCurrentShelf(
				{ id: "produce", name: "Prateleira 1" },
				() => assignments,
			);

		expect(handleShelfPress().productId).toBe(1);

		assignments = { produce: null };
		expect(handleShelfPress().productId).toBeUndefined();

		assignments = { produce: 5 };
		expect(handleShelfPress().productId).toBe(5);
	});
});
