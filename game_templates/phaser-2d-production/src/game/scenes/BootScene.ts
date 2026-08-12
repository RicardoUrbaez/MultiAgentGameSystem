import { Scene } from 'phaser';

export class BootScene extends Scene {
    public constructor() {
        super('BootScene');
    }

    public create(): void {
        this.scale.on('resize', () => this.cameras.main.centerOn(512, 384));
        this.scene.start('PreloadScene');
    }
}
