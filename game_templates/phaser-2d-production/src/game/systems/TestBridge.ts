import { RuntimeState } from '../state/GameState';

declare global {
    interface Window {
        __GAME_TEST__?: GameTestBridge;
    }
}

export type GameTestBridge = {
    getState: () => RuntimeState;
    reset: () => void;
    getErrors: () => string[];
    errors: string[];
    setScore?: (score: number) => void;
    spawnEnemy?: () => void;
    teleportPlayer?: (x: number, y: number) => void;
    getEntities?: () => RuntimeState['enemies'];
    advanceState?: (milliseconds: number) => void;
    triggerWin?: () => void;
    triggerLoss?: () => void;
};

export class TestBridge {
    private readonly errors: string[] = [];

    public constructor() {
        window.addEventListener('error', (event) => this.recordError(event.message));
        window.addEventListener('unhandledrejection', (event) => this.recordError(String(event.reason)));
    }

    public install(bridge: Omit<GameTestBridge, 'errors' | 'getErrors'>): void {
        window.__GAME_TEST__ = {
            ...bridge,
            errors: this.errors,
            getErrors: () => [...this.errors]
        };
    }

    public recordError(error: string): void {
        this.errors.push(error);
    }
}
