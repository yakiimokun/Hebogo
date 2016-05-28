//
// @file UCT
struct UCTChild {
    var move:Int        // move position
    var games:Int       // number of games
    var rate:Double     // win rate
    var node:UCTNode?   // next node

    init(_ move:Int) {
        self.move  = move
        self.games = 0
        self.rate  = 0
        self.node  = nil
    }
}
