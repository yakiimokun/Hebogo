//
// PrimitiveMonteCarloPlayer.swift
//
// Created by yakiimokun on 2/28/16
// Copyright 2016 yakiimokun. All rights reserved 
//
struct PrimitiveMonteCarloPlayer : Player {
    /*
     * @func putMove
     * @brief choose the highest UCB value 
     * @param color 
     *
     */
    func selectBestMove(color:Int, inout _ board:Board) -> Int {
        var bestValue:Double = -100
        var bestMove:Int     = 0
        let tryNum:Int       = 30                  
        var winRate:Double

        var currentBoard:Board = board
        
        // try all empty point
        for (move, stoneColor) in currentBoard.squares.enumerate() {
            var winSum:Int = 0
            if (stoneColor != board.BLANK) {
                continue
            }

            if (currentBoard.RETURN_OK != currentBoard.putStone(move, color, currentBoard.FILL_EYE_ERR)) {
                continue
            }
            
            // try playout
            for _ in 1...tryNum {
                var copyBoard:Board  = board
                let win:Int          = -1 * copyBoard.executePlayOut(copyBoard.flipColor(color))
                winSum              += win
            }

            winRate = Double(winSum) / Double(tryNum)

            if (winRate > bestValue) {
                bestValue = winRate
                bestMove  = move
            }
        }

        return bestMove
    }
}
