//if Process.arguments.count < 3 {
//    print("Usage : black white")
//    return
//}
var board:Board         = Board()
var player:[Int:Player] = [board.BLACK:UCTPlayer(), board.WHITE:PrimitiveMonteCarloPlayer()]
var color:Int           = board.BLACK

//for arg in Process.arguments {
//    if (arg.hasPrefix("-bp=") || arg.hasPrefix("-wp=")) {
//        let method = arg.substringFromIndex(advance(arg.startIndex, 4))
//        switch method {
//            case "MonteCarlo":
//                player.append(PrimitiveMonteCarloPlayer(), atInex:board.BLACK)
//                break
//            case "UCT":
//                player.append(UCTPlayer(), atIndex:board.WHITE)
//                break
//            default:
//                break
//        }
//    }
//}

var pos:Int
var ret:Int

while(true) {
    pos = player[color]!.selectBestMove(color, &board)
    print("pos = \(pos)")
    ret = board.putStone(pos, color, board.FILL_EYE_OK)
    board.printStone()
    color = board.flipColor(color)
}


