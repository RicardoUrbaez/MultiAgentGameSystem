import { BootScene } from './scenes/BootScene';
import { GameOverScene } from './scenes/GameOverScene';
import { GameScene } from './scenes/GameScene';
import { MenuScene } from './scenes/MenuScene';
import { CANVAS, Game, Scale, Types } from 'phaser';
import { PreloadScene } from './scenes/PreloadScene';

//  Find out more information about the Game Config at:
//  https://docs.phaser.io/api-documentation/typedef/types-core#gameconfig
const config: Types.Core.GameConfig = {
    type: CANVAS,
    width: 1024,
    height: 768,
    parent: 'game-container',
    backgroundColor: '#08111f',
    scale: {
        mode: Scale.FIT,
        autoCenter: Scale.CENTER_BOTH,
        width: 1024,
        height: 768
    },
    physics: {
        default: 'arcade',
        arcade: {
            debug: false
        }
    },
    scene: [
        BootScene,
        PreloadScene,
        MenuScene,
        GameScene,
        GameOverScene
    ]
};

const StartGame = (parent: string) => {

    return new Game({ ...config, parent });

}

export default StartGame;
