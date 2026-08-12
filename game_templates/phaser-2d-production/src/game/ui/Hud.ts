import { GameObjects, Scene } from 'phaser';
import { RuntimeState } from '../state/GameState';

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

    public update(state: RuntimeState): void {
        this.scoreText.setText(`Score ${state.score}   Lives ${state.lives}   Level ${state.level}`);
        this.objectiveText.setText(`Objective ${state.objectiveProgress}/${state.objectiveTarget}`);
        this.statusText.setText(state.gameOver ? `${state.winner ?? 'Game over'} - press R to restart` : state.paused ? 'Paused - press Esc to resume' : 'Active');
    }
}
