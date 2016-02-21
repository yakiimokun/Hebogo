if Process.arguments.count != 2 {
    print("Usage : boardSize")
} else {
    var board:Board = Board(boardSize:Int(Process.arguments[1])!)
    var color:Int   = board.BLACK
    var pos:Int
    var ret:Int
    
    for _ in 1...30 {
        pos = board.executeMonteCarlo(color)
        ret = board.putStone(pos, color, board.FILL_EYE_OK)
        board.printStone()
        color = (color == board.BLACK) ? board.WHITE : board.BLACK
    }
}
