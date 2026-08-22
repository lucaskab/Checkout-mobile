# Welcome to your Expo app 👋

Checkout is an Expo/React Native mobile app with the Market Simulator embedded
natively through LibGodot. The editable Godot project lives in `godot/`; fresh
mobile exports live in `godot-exports/` and are committed for reproducible builds.

## Continue development on macOS

Install these prerequisites first:

- Xcode and its command-line tools;
- CocoaPods;
- Android Studio/JDK 17 if you also build Android;
- Bun or Node.js;
- Godot 4.5.1 (standard app in `/Applications/Godot.app`).

Then clone and prepare the project:

```bash
git clone https://github.com/lucaskab/Checkout-mobile.git
cd Checkout-mobile
bun install
bunx expo prebuild --clean
```

`bun install` downloads the official LibGodot 4.5.1 native packages for iOS and
Android and applies the React Native 0.86 compatibility adjustments. The Expo
config plugin copies the committed Android export and the iOS PCK into the native
projects during prebuild.

Run on a physical iPhone:

```bash
bunx expo run:ios --device
```

Run on a physical ARM Android device:

```bash
bun android --device
```

The simulator is native and is not available in Expo Go. The current Android
LibGodot binaries target ARM devices; x86 Android emulators display the safe
compatibility screen. The app also deliberately uses that screen in an iOS
Simulator, while the complete simulator runs on a physical iPhone.

## Develop and export the Godot game

Open `godot/project.godot` in Godot 4.5.1. Scenes, GDScript, textures, import
settings and development tools are all versioned there. The `.godot/` directory
is only an editor cache and is intentionally ignored.

After changing the game, regenerate both mobile exports:

```bash
bun run godot:export
```

This produces:

- `godot-exports/android/CheckoutMarket/` for Android APK assets;
- `godot-exports/ios/CheckoutMarket.pck` for the iOS application bundle.

If `android/` already exists, the export command updates its embedded game too.
For iOS, run `bunx expo prebuild --clean` after a new export so Xcode receives the
latest PCK.

This is an [Expo](https://expo.dev) project created with [`create-expo-app`](https://www.npmjs.com/package/create-expo-app).

## Get started

1. Install dependencies

   ```bash
   npm install
   ```

2. Start the app

   ```bash
   npx expo start
   ```

In the output, you'll find options to open the app in a

- [development build](https://docs.expo.dev/develop/development-builds/introduction/)
- [Android emulator](https://docs.expo.dev/workflow/android-studio-emulator/)
- [iOS simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Expo Go](https://expo.dev/go), a limited sandbox for trying out app development with Expo

## RevenueCat purchases

1. Create the 15 consumable products from `src/data/currency-packs.ts` in App Store Connect and Google Play Console using the exact `productId` values.
2. Import the products into RevenueCat and attach them to the iOS and Android apps.
3. Copy `.env.example` to `.env.local` and set the public RevenueCat keys. The test key is used in development when present; release builds use the platform-specific keys.
4. Rebuild the development client after installing or updating `react-native-purchases`. Real purchases are not available through Expo Go.

The displayed price always comes from the store. The euro values in the local catalog are placeholders shown only while a product is unavailable.

You can start developing by editing the files inside the **app** directory. This project uses [file-based routing](https://docs.expo.dev/router/introduction).

## Get a fresh project

When you're ready, run:

```bash
npm run reset-project
```

This command will move the starter code to the **app-example** directory and create a blank **app** directory where you can start developing.

### Other setup steps

- To set up ESLint for linting, run `npx expo lint`, or follow our guide on ["Using ESLint and Prettier"](https://docs.expo.dev/guides/using-eslint/)
- If you'd like to set up unit testing, follow our guide on ["Unit Testing with Jest"](https://docs.expo.dev/develop/unit-testing/)
- Learn more about the TypeScript setup in this template in our guide on ["Using TypeScript"](https://docs.expo.dev/guides/typescript/)

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.
