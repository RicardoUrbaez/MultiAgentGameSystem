import { Scene } from 'phaser';

export class MenuScene extends Scene {
    public constructor() {
        super('MenuScene');
    }

    public create(): void {
        this.cameras.main.setBackgroundColor('#08111f');
        this.add.text(512, 250, 'Production Phaser Game', {
            fontFamily: 'Trebuchet MS', fontSize: '44px', color: '#eaf6ff'
        }).setOrigin(0.5);
        this.add.text(512, 340, 'Arrow keys or WASD move. Space gains score. Esc pauses.', {
            fontFamily: 'Trebuchet MS', fontSize: '20px', color: '#72f1b8'
        }).setOrigin(0.5);
        this.add.text(512, 430, 'Press Space or click to start', {
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#ffe66d'
        }).setOrigin(0.5);
        this.input.once('pointerdown', () => this.scene.start('GameScene'));
        this.input.keyboard?.once('keydown-SPACE', () => this.scene.start('GameScene'));
    }
}
