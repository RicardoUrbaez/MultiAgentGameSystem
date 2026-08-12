import { Scene } from 'phaser';

export class AudioSystem {
    public constructor(private readonly scene: Scene) {}

    public play(key: string): void {
        if (this.scene.cache.audio.exists(key)) {
            this.scene.sound.play(key);
        }
    }
}
