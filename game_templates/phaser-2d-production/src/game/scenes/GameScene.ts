import { GameObjects, Scene } from 'phaser';
import { Hud } from '../ui/Hud';
import { createInitialState, EntityState, RuntimeState } from '../state/GameState';
import { AudioSystem } from '../systems/AudioSystem';
import { EffectsSystem } from '../systems/EffectsSystem';
import { InputSystem } from '../systems/InputSystem';
import { ProgressionSystem } from '../systems/ProgressionSystem';
import { ScoreSystem } from '../systems/ScoreSystem';
import { TestBridge } from '../systems/TestBridge';

export class GameScene extends Scene {
    private state = createInitialState();
    private player!: GameObjects.Image;
    private enemySprites = new Map<string, GameObjects.Image>();
    private inputSystem!: InputSystem;
    private scoreSystem = new ScoreSystem();
    private progressionSystem = new ProgressionSystem();
    private hud!: Hud;
    private effects!: EffectsSystem;
    private audio!: AudioSystem;
    private bridge!: TestBridge;

    public constructor() {
        super('GameScene');
    }

    public create(): void {
        this.cameras.main.setBackgroundColor('#08111f');
        this.add.tileSprite(512, 384, 1024, 768, 'placeholder-tile').setAlpha(0.5);
        this.player = this.add.image(this.state.player.x, this.state.player.y, 'placeholder-player').setScale(1.5);
        this.inputSystem = new InputSystem(this);
        this.hud = new Hud(this);
        this.effects = new EffectsSystem(this);
        this.audio = new AudioSystem(this);
        this.bridge = new TestBridge();
        this.effects.transitionIn();
        this.installTestBridge();
        this.spawnEnemy();
        this.refreshHud();
    }

    public update(_time: number, delta: number): void {
        if (this.inputSystem.pausePressed) {
            this.state.paused = !this.state.paused;
        }
        if (this.state.paused || this.state.gameOver) {
            this.refreshHud();
            return;
        }
        const movement = this.inputSystem.getMovement();
        const speed = 0.26 * delta;
        this.state.player.x = Phaser.Math.Clamp(this.state.player.x + movement.x * speed, 24, 1000);
        this.state.player.y = Phaser.Math.Clamp(this.state.player.y + movement.y * speed, 112, 744);
        this.player.setPosition(this.state.player.x, this.state.player.y);
        if (this.inputSystem.actionPressed) {
            this.scorePoint(1);
        }
        this.refreshHud();
    }

    private installTestBridge(): void {
        this.bridge.install({
            getState: () => this.snapshot(),
            reset: () => this.reset(),
            setScore: (score) => this.setScore(score),
            spawnEnemy: () => this.spawnEnemy(),
            teleportPlayer: (x, y) => this.teleportPlayer(x, y),
            getEntities: () => this.snapshot().enemies,
            advanceState: (milliseconds) => this.advanceState(milliseconds),
            triggerWin: () => this.endGame('Victory'),
            triggerLoss: () => this.endGame('Defeat')
        });
    }

    private snapshot(): RuntimeState {
        return JSON.parse(JSON.stringify(this.state)) as RuntimeState;
    }

    private reset(): void {
        this.state = createInitialState();
        this.scoreSystem.reset();
        this.progressionSystem.reset();
        this.player.setPosition(this.state.player.x, this.state.player.y);
        for (const sprite of this.enemySprites.values()) {
            sprite.destroy();
        }
        this.enemySprites.clear();
        this.spawnEnemy();
        this.refreshHud();
    }

    private setScore(score: number): void {
        this.scoreSystem.set(score);
        this.state.score = this.scoreSystem.score;
        this.refreshHud();
    }

    private scorePoint(points: number): void {
        if (this.state.gameOver) {
            return;
        }
        this.state.score = this.scoreSystem.add(points);
        if (this.progressionSystem.addProgress(points)) {
            const progress = this.progressionSystem.getState();
            this.state.level = progress.level;
            this.state.objectiveProgress = progress.progress;
            this.state.objectiveTarget = progress.target;
            this.spawnEnemy();
        } else {
            const progress = this.progressionSystem.getState();
            this.state.objectiveProgress = progress.progress;
        }
        this.effects.hitFeedback(this.player);
        this.audio.play('placeholder-sound');
        if (this.state.score >= 10) {
            this.endGame('Victory');
        }
    }

    private spawnEnemy(): void {
        const id = `enemy-${this.state.enemies.length + 1}`;
        const entity: EntityState = { id, type: 'enemy', x: Phaser.Math.Between(80, 944), y: Phaser.Math.Between(150, 680), active: true };
        this.state.enemies.push(entity);
        this.enemySprites.set(id, this.add.image(entity.x, entity.y, 'placeholder-enemy'));
    }

    private teleportPlayer(x: number, y: number): void {
        this.state.player.x = Phaser.Math.Clamp(x, 24, 1000);
        this.state.player.y = Phaser.Math.Clamp(y, 112, 744);
        this.player.setPosition(this.state.player.x, this.state.player.y);
    }

    private advanceState(milliseconds: number): void {
        const points = Math.max(0, Math.floor(milliseconds / 1000));
        if (points > 0) {
            this.scorePoint(points);
        }
    }

    private endGame(winner: string): void {
        this.state.running = false;
        this.state.gameOver = true;
        this.state.winner = winner;
        this.refreshHud();
    }

    private refreshHud(): void {
        this.hud.update(this.state);
    }
}
