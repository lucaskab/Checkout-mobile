# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v57.0.0/ before writing any code.

For animations, use the `react-native-reanimated` library.
For lists use `@legendapp/list` library. import { LegendList, LegendListRef, LegendListRenderItemProps } from "@legendapp/list/react-native"

For bottom sheets, use the reusable component from `react-native-bottom-sheet`.

For any styling, use `react-native-unistyles` library with it's tokens, to have access to the theme tokens you can use this as example:

```tsx
import { StyleSheet } from "react-native-unistyles";

const styles = StyleSheet.create((theme, rt) => ({
    container: {
        backgroundColor: theme.colors.background,
        variants: {
            size: {
                small: {
                    width: 100,
                    height: 100
                },
                medium: {
                    width: 200,
                    height: 200
                },
                large: {
                    width: 300,
                    height: 300
                }
            },
            isPrimary: {
                true: {
                    color: theme.colors.primary
                },
                default: {
                    color: theme.colors.secondary
                },
                special: {
                    color: theme.colors.special
                }
            }
        }
    },
    text: {
        fontSize: rt.fontScale * 20,
        color: {
            sm: theme.colors.text,
            md: theme.colors.textSecondary
        }
    })
}))
```

Also, here is the unistyles documentation: https://www.unistyl.es/v3/references/stylesheet/

Always use good archtecture and good coding practices
Always create the content of the screens inside a folder inside the `screens` folder, and then call the component inside the file inside the app folder because we are using Expo Router

Create reusable types inside the `@types` folder
