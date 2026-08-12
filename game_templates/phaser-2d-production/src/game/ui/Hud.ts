import { GameObjects, Scene } from 'phaser';
import { RuntimeState } from '../state/GameState';

type HudState = Partial<RuntimeState> & {
    isGameOver?: boolean;
    distance?: number;
};

export class Hud {
    private readonly scoreText: GameObjects.Text;
    private readonly objectiveText: GameObjects.Text;
    private readonly statusText: GameObjects.Text;

    public constructor(scene: Scene) {
        const style = { fontFamily: 'Trebuchet MS', fontSize: '18px', color: '#eaf6ff' };
        this.scoreText = scene.add.text(20, 18, '', style).setScrollFactor(0);
        this.objectiveText = scene.add.text(20, 44, '', style).setScrollFactor(0);
        this.statusText = scene.add.text(20, 70, '', { ...style, color: '#72f1b8' }).setScrollFactor(0);
    }

    public update(state: HudState): void {
        const score = state.score ?? state.distance ?? 0;
        const lives = state.lives ?? 1;
        const level = state.level ?? 1;
        const objectiveProgress = state.objectiveProgress ?? 0;
        const objectiveTarget = state.objectiveTarget ?? 0;
        const gameOver = state.gameOver ?? state.isGameOver ?? false;
        const paused = state.paused ?? false;

        this.scoreText.setText(`Score ${score}   Lives ${lives}   Level ${level}`);
        this.objectiveText.setText(objectiveTarget > 0 ? `Objective ${objectiveProgress}/${objectiveTarget}` : '');
        this.statusText.setText(gameOver ? `${state.winner ?? 'Game over'} - press R to restart` : paused ? 'Paused - press Esc to resume' : 'Active');
    }
}
