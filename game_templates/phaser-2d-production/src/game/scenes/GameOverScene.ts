import { Scene } from 'phaser';

export class GameOverScene extends Scene {
    public constructor() {
        super('GameOverScene');
    }

    public create(data: { winner?: string; score?: number }): void {
        this.cameras.main.setBackgroundColor('#140f20');
        this.add.text(512, 320, data.winner ?? 'Game Over', {
            fontFamily: 'Trebuchet MS', fontSize: '48px', color: '#ffffff'
        }).setOrigin(0.5);
        this.add.text(512, 385, `Final score: ${data.score ?? 0}`, {
            fontFamily: 'Trebuchet MS', fontSize: '24px', color: '#ffe66d'
        }).setOrigin(0.5);
        this.add.text(512, 455, 'Press Space or click for the menu', {
            fontFamily: 'Trebuchet MS', fontSize: '20px', color: '#72f1b8'
        }).setOrigin(0.5);
        this.input.once('pointerdown', () => this.scene.start('MenuScene'));
        this.input.keyboard?.once('keydown-SPACE', () => this.scene.start('MenuScene'));
    }
}
