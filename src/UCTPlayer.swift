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
    /*
     * @func  putMove (color:Int) -> Int
     * @param color
     * @return choosed position
     */
     func selectBestMove(color:Int, inout _ board:Board) -> Int {
        var max:Int         = -999
        var bestMove:Int    = 0
        let trials:Int      = 1000
        var uctNode:UCTNode = createNodes(board)

        for _ in 1...trials {
            var copyBoard:Board = board
            searchUCT(color, &uctNode, &copyBoard)
        }

        for child in uctNode.children {
            if (child.games > max) {
                bestMove = child.move
                max      = child.games
            }
        }

        return bestMove
    }

    /*
     * @brief search UCT
     * @return 
     */
     func searchUCT(color:Int, inout _ node:UCTNode, inout _ board:Board) -> Int {
         var ret:Int
         var win:Int
         var selectedIndex:Int = 0
         
         while(true) {
             selectedIndex = selectBestUCBIndex(node, &board)
             ret           = board.putStone(node.children[selectedIndex].move, color, board.FILL_EYE_ERR)
            
             if (ret == board.RETURN_OK) {
                 break
             }

             node.children[selectedIndex].move = board.ILLEGAL
         }

         if (node.children[selectedIndex].games <= 0) {
             win = -1 * board.executePlayOut(board.flipColor(color))
         } else {
             if (node.children[selectedIndex].node == nil) {
                 node.children[selectedIndex].node = createNodes(board)
             }

             win = -1 * searchUCT(board.flipColor(color), &node.children[selectedIndex].node!, &board)
         }

         // update winRate
         node.children[selectedIndex].rate   = (node.children[selectedIndex].rate *
                                                  Double(node.children[selectedIndex].games) + Double(win)) /
                                               (Double(node.children[selectedIndex].games) + 1.0)
         node.children[selectedIndex].games += 1
         node.gamesSUM                      += 1

         // print("color = \(color), rate = \(node.children[selectedIndex].rate), games = \(node.children[selectedIndex].games), win = \(win)")                  
         return win
    }

    /*
     * @brief select best UCB
     */
     func selectBestUCBIndex(pNode:UCTNode, inout _ board:Board) -> Int {
         var UCB:Double              = 0.0
         var maxUCB:Double           = -999.0
         var selectedIndex:Int       = -1

         for (i, child) in pNode.children.enumerate() {
             if (child.move == board.ILLEGAL) {
                 continue
             }

             if (child.games == 0) {
                 UCB = 10000.0 + Double(rand(0x7fff));
             } else {
                 let C:Double = 1.0
                 UCB = child.rate + C * sqrt(log(Double(pNode.gamesSUM)) / Double(child.games))
             }

             if (UCB > maxUCB) {
                 maxUCB        = UCB
                 selectedIndex = i
             }
         }

         if (selectedIndex == -1) {
             exit(0)
         }
         return selectedIndex
     }

    /*
     * @brief  create new Node
     * @param  board
     * @return node 
     */
     func createNodes(board:Board) -> UCTNode {
         var node = UCTNode(0)

         for y in 1...board.squaresSize {
             for x in 1...board.squaresSize {
                 if (board.getColor(x, y) != board.BLANK) {
                     continue
                 }

                 node.children.append(UCTChild(board.Position(x, y)))
             }
         }

         node.children.append(UCTChild(0))
         return node
     }
}
