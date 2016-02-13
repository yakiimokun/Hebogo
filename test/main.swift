//
// main.swift (for unit test)
// Created by yakiimokun
// Copyright 2016 yakiimokun All rights reserved.
//
let test        = TAP(tests:8) 
var board:Board = Board(boardSize:9)

// take stone test
test.eq(board.putStone(board.Position(2, 1), board.WHITE, board.FILL_EYE_OK), board.RETURN_OK, "putStone is OK")

board.putStone(board.Position(1, 2), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(2, 2), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(3, 2), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(4, 2), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(5, 2), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(1, 3), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(2, 3), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(3, 3), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(4, 3), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(5, 3), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(6, 3), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(2, 4), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(3, 4), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(4, 4), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(5, 4), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(3, 5), board.WHITE, board.FILL_EYE_OK)

test.eq(board.getColor(2, 2), board.BLANK, "black stone is taken")
test.eq(board.getColor(2, 3), board.BLANK, "black stone is taken")
test.eq(board.getColor(3, 3), board.BLANK, "black stone is taken")
test.eq(board.getColor(4, 3), board.BLANK, "black stone is taken")
test.eq(board.getColor(5, 3), board.BLANK, "black stone is taken")
test.eq(board.getColor(3, 4), board.BLANK, "black stone is taken")

// ko test
board.putStone(board.Position(6, 5), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(7, 5), board.WHITE, board.FILL_EYE_OK)

board.putStone(board.Position(5, 6), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(6, 6), board.WHITE, board.FILL_EYE_OK)
board.putStone(board.Position(8, 6), board.WHITE, board.FILL_EYE_OK)
    
board.putStone(board.Position(6, 7), board.BLACK, board.FILL_EYE_OK)
board.putStone(board.Position(7, 7), board.WHITE, board.FILL_EYE_OK)        
    
board.putStone(board.Position(7, 6), board.BLACK, board.FILL_EYE_OK)

test.eq(board.putStone(board.Position(6, 6), board.WHITE, board.FILL_EYE_OK), board.RETURN_KO, "ko is occurred !!")
test.done()

