import { Scene } from 'phaser';

const ASSETS = [
    ['placeholder-player', 'assets/library/characters/placeholder-player.svg'],
    ['placeholder-enemy', 'assets/library/enemies/placeholder-enemy.svg'],
    ['placeholder-tile', 'assets/library/environment/placeholder-tile.svg'],
    ['placeholder-projectile', 'assets/library/projectiles/placeholder-projectile.svg'],
    ['placeholder-panel', 'assets/library/ui/placeholder-panel.svg'],
    ['placeholder-spark', 'assets/library/fx/placeholder-spark.svg']
] as const;

export class PreloadScene extends Scene {
    public constructor() {
        super('PreloadScene');
    }

    public preload(): void {
        const bar = this.add.rectangle(512, 384, 0, 12, 0x72f1b8).setOrigin(0, 0.5);
        this.load.on('progress', (value: number) => bar.width = 360 * value);
        for (const [key, path] of ASSETS) {
            this.load.svg(key, path);
        }
    }

    public create(): void {
        this.scene.start('MenuScene');
    }
}
