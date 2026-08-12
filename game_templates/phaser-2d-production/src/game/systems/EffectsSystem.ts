import { GameObjects, Scene } from 'phaser';

export class EffectsSystem {
    public constructor(private readonly scene: Scene) {}

    public hitFeedback(target: GameObjects.GameObject): void {
        this.scene.cameras.main.shake(80, 0.003);
        this.scene.tweens.add({
            targets: target,
            alpha: 0.25,
            duration: 60,
            yoyo: true,
            repeat: 2
        });
    }

    public transitionIn(): void {
        this.scene.cameras.main.fadeIn(180, 8, 16, 32);
    }
}
