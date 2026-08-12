export class ProgressionSystem {
    public constructor(private progress = 0, private target = 10, private level = 1) {}

    public addProgress(amount: number): boolean {
        this.progress = Math.max(0, this.progress + amount);
        if (this.progress < this.target) {
            return false;
        }
        this.level += 1;
        this.progress = 0;
        this.target += 5;
        return true;
    }

    public reset(): void {
        this.progress = 0;
        this.target = 10;
        this.level = 1;
    }

    public getState(): { progress: number; target: number; level: number } {
        return { progress: this.progress, target: this.target, level: this.level };
    }
}
