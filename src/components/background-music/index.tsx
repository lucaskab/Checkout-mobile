import { setAudioModeAsync, useAudioPlayer } from "expo-audio";
import { useEffect } from "react";

const backgroundMusic = require("../../../assets/audios/background_music.mp3");

export function BackgroundMusic() {
	const player = useAudioPlayer(backgroundMusic);

	useEffect(() => {
		void setAudioModeAsync({
			playsInSilentMode: true,
			shouldPlayInBackground: false,
		});
		player.loop = true;
		player.volume = 0.35;
		player.play();
	}, [player]);

	return null;
}
