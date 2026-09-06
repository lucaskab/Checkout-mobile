const fs = require("fs");
const path = require("path");
const { withAndroidManifest, withGradleProperties } = require("expo/config-plugins");

/**
 * Unity exports enable Android's predictive-back callback by default. Expo's
 * Android manifest intentionally disables it, so the app manifest must win
 * during the native manifest merge.
 */
const withUnityManifest = (config) =>
	withAndroidManifest(config, (mod) => {
		const application = mod.modResults.manifest.application?.[0];
		if (!application) return mod;
		const current = application.$["tools:replace"]
			?.split(",")
			.map((value) => value.trim())
			.filter(Boolean) ?? [];
		if (!current.includes("android:enableOnBackInvokedCallback")) {
			current.push("android:enableOnBackInvokedCallback");
		}
		application.$["tools:replace"] = current.join(",");
		return mod;
	});

const withUnityBuildPaths = (config) =>
	withGradleProperties(config, (mod) => {
		const exportedProperties = path.join(
			mod.modRequest.projectRoot,
			"unity",
			"builds",
			"android",
			"gradle.properties",
		);
		if (!fs.existsSync(exportedProperties)) return mod;
		const values = Object.fromEntries(
			fs
				.readFileSync(exportedProperties, "utf8")
				.split(/\r?\n/)
				.map((line) => line.trim())
				.filter((line) => line.includes("="))
				.map((line) => line.split(/=(.*)/s).map((part) => part.trim())),
		);
		for (const key of [
			"unity.androidSdkPath",
			"unity.androidNdkPath",
			"unity.jdkPath",
		]) {
			if (!values[key]) continue;
			const existing = mod.modResults.find((item) => item.key === key);
			if (existing) existing.value = values[key];
			else mod.modResults.push({ type: "property", key, value: values[key] });
		}
		const architectures = mod.modResults.find(
			(item) => item.key === "reactNativeArchitectures",
		);
		if (architectures) architectures.value = "arm64-v8a";
		else {
			mod.modResults.push({
				type: "property",
				key: "reactNativeArchitectures",
				value: "arm64-v8a",
			});
		}
		return mod;
	});

module.exports = (config) => withUnityBuildPaths(withUnityManifest(config));
