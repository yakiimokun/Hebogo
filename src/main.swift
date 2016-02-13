if Process.arguments.count != 2 {
    print("Usage : boardSize")
} else {
    var board:Board = Board(boardSize:Int(Process.arguments[1])!)
    board.executePlayOut(board.BLACK)
}
