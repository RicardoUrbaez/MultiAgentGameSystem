import { Input, Scene } from 'phaser';

export class InputSystem {
    private readonly cursors: Phaser.Types.Input.Keyboard.CursorKeys;
    private readonly keys: Record<string, Input.Keyboard.Key>;

    constructor(scene: Scene) {
        const keyboard = scene.input.keyboard;
        if (!keyboard) {
            throw new Error('Keyboard input is unavailable.');
        }
        this.cursors = keyboard.createCursorKeys();
        this.keys = keyboard.addKeys('W,A,S,D,SPACE,ESC') as Record<string, Input.Keyboard.Key>;
    }

    getMovement(): { x: number; y: number } {
        const x = Number(this.cursors.left?.isDown || this.keys.A.isDown) - Number(this.cursors.right?.isDown || this.keys.D.isDown);
        const y = Number(this.cursors.up?.isDown || this.keys.W.isDown) - Number(this.cursors.down?.isDown || this.keys.S.isDown);
        return { x, y };
    }

    get pausePressed(): boolean {
        return Input.Keyboard.JustDown(this.keys.ESC);
    }

    get actionPressed(): boolean {
        return Input.Keyboard.JustDown(this.keys.SPACE);
    }
}
