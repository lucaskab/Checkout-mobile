// node:path for the embedded build: the page code only takes file names apart (icon ids).
export function basename(path: string, ext?: string) {
	const name = path.replace(/\\/g, "/").split("/").pop() ?? "";
	return ext && name.endsWith(ext) ? name.slice(0, -ext.length) : name;
}
export function extname(path: string) {
	const name = basename(path);
	const at = name.lastIndexOf(".");
	return at > 0 ? name.slice(at) : "";
}
export function dirname(path: string) {
	const parts = path.replace(/\\/g, "/").split("/");
	parts.pop();
	return parts.join("/") || ".";
}
export function join(...parts: string[]) {
	return parts.filter(Boolean).join("/").replace(/\/+/g, "/");
}
export const resolve = join;
export default { basename, extname, dirname, join, resolve };
