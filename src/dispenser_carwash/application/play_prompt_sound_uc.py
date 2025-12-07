from dispenser_carwash.domain.interfaces.hardware.i_sound import ISound


class PlayPromptSoundUseCase:
    def __init__(self, sound_player: ISound):
        self.sound_player = sound_player

    def execute(self, prompt_key: str, force: bool = False):
        """
        Play prompt by key name.
        force=True -> interrupt current sound if playing.
        """
        if force:
            self.sound_player.stop()

        self.sound_player.play(prompt_key)

    def stop(self):
        self.sound_player.stop()
