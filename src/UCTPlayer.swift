//
// @file UCTPlayer.swift
//
// Created by yakiimokun on 2/28/16
// Copyright 2016 yakiimokun. All rights reserved
//
#if os(Linux)
    import Glibc    
#endif    

struct UCTPlayer : Player {
     var record:[Int]
     var moves:Int

     init() {
         self.record         = [Int](repeating:0, count:1000)
         self.moves         = 0
     }
     
   /*
     * @func  putMove (color:Int) -> Int
     * @param color
     * @return choosed position
     */
     func selectBestMove(_ color:Stone, _ board: Board) -> Int {
        var max:Double      = -999
        var bestMove:Int   = 0
        var root:UCTNode = UCTNode(0, 0, 0)
        let training:Int       = 10000
        
        expandChild(&root, color, board)

        // choose UCB
        while root.playout < training {
            var copyBoard:Board = board
            var currentColor          = color

            let candidate:UCTNode? = searchCandidate(1, root, &currentColor, &copyBoard)

            if (candidate != nil) {
                let win:Int = doPlayOut(candidate!.move, color, &copyBoard)
                candidate!.propagateResult(1, win)
            }
        }
        
        for child in root.children {
            let rate:Double = Double(child.win) / Double(child.playout) 
            if (rate > max) {
                bestMove = child.move
                max             = rate
            }
        }

        return bestMove
    }

    /*
     * @brief search UCT
     * @return 
     */
     func expandChild(_ node:inout UCTNode, _ color:Stone,  _ board: Board) {
         var totalPlayOut:Int = 0
         var totalWin:Int          = 0
         
         if (node.children.count != 0) {
             return
         }

         for (pos, color) in board.squares.enumerated() {
             if (color != .BLANK) {
                 continue
             }

             var copy:Board            = board
             let child:UCTNode    = UCTNode(pos, 1,  doPlayOut(pos, color, &copy))
             totalPlayOut             += 1
             totalWin                      += child.win

             node.addChild(child) 
         }

         node.propagateResult(totalPlayOut, totalWin)
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

     func searchCandidate(_ sign:Double, _ parent:UCTNode, _ turnColor:inout Stone, _ board:inout Board) -> UCTNode {
         var candidate:UCTNode = parent.selectChild(sign)
         var ret:ReturnCode

         if (board.empty.count != 0) { 
             ret               = board.putStone(candidate.move, turnColor, .FOR_PLAYOUT)
             if (ret != .RETURN_OK) {
                 return candidate
             }

             turnColor = (turnColor == .BLACK) ? .WHITE : .BLACK

             expandChild(&candidate, turnColor, board)

             candidate = searchCandidate(-1 * sign, candidate, &turnColor, &board)
         }

         return candidate
     }
}
