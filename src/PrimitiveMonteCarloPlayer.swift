//
// PrimitiveMonteCarloPlayer.swift
//
// Created by yakiimokun on 2/28/16
// Copyright 2016 yakiimokun. All rights reserved 
//
#if os(Linux)
    import Glibc
#endif    

struct PrimitiveMonteCarloPlayer : Player {
    /*
     * @func putMove
     * @brief choose the highest UCB value 
     * @param color 
     *
     */
    func selectBestMove(_ color:Stone, _ board: Board) -> Int {
        var bestValue:Double = -100
        var bestMove:Int     = 0
        let tryNum:Int       = 30                  
        var winRate:Double

        let currentBoard:Board = board
        
        // try all empty point
        for (move, stoneColor) in currentBoard.squares.enumerated() {
            var winSum:Int = 0
            if (stoneColor != .BLANK) {
                continue
            }

            // try playout
            for _ in 1...tryNum {
                var copyBoard:Board    = board
                let win:Int                          = doPlayOut(move, copyBoard.flipColor(color), &copyBoard)
                winSum                            += win
            }

            winRate = Double(winSum) / Double(tryNum)

            if (winRate > bestValue) {
                bestValue = winRate
                bestMove  = move
            }
        }
        return bestMove
    }
        
    /*
     * @brief actually play out
     * TODO: this method should move the class for thinking routine
     */
     func doPlayOut(_ pos:Int,  _ turnColor:Stone, _ board:inout Board) -> Int {
        // to prevent the eternal loop by triple ko                
        var tempColor:Stone      = turnColor
        var previous_choice:Int = 0
        let trials:Int                         = board.squaresSize * board.squaresSize + 200

        let ret:ReturnCode = board.putStone(pos, turnColor, .FOR_PLAYOUT)
        if (ret != .RETURN_OK) {
            return -1
        }
        
        var choice:Int       = 0
        for _ in 1...trials {
            while (true) {
                var ret:ReturnCode
                var index:Int = -1

                if (board.empty.count == 0) {
                    choice = 0
                } else {
                    index    = Int(rand()) % Int(board.empty.count)
                    choice  = board.empty[index]
                }

                ret = board.putStone(choice, tempColor, .FOR_PLAYOUT)
                if (ret == .RETURN_OK) {
                    break
                }

                if (index != -1) {
                    board.empty.remove(at:index)
                }
            }

            if (choice == 0 && previous_choice == 0) {
                break;
            }
            
            previous_choice = choice
            // board.printStone()

            // print("choice = \(choice) color = \(tempColor) ko = \(koPos)")
            tempColor     = (tempColor == .BLACK) ? .WHITE : .BLACK
        }

        return board.countScore(turnColor)
     }
}
