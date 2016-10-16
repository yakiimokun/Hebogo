//
// @file main.swift (for unit test)
// Created by yakiimokun 10/1/16
// Copyright 2016 yakiimokun All rights reserved.
//
#if os(Linux)
    import Glibc
#else
    import Darwin
#endif         

let test                   = TAP(tests:23) 
var board:Board = Board(9)

// take stone test
test.eq(board.putStone(board.Position(2, 1), .WHITE, .FOR_MOVE), .RETURN_OK, "putStone is OK")

var ret:ReturnCode
ret = board.putStone(board.Position(1, 2), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(2, 2), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(3, 2), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(4, 2), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(5, 2), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(1, 3), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(2, 3), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(3, 3), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(4, 3), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(5, 3), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(6, 3), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(2, 4), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(3, 4), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(4, 4), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(5, 4), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(3, 5), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}

test.eq(board.getColor(2, 2), .BLANK, "black stone is taken")
test.eq(board.getColor(2, 3), .BLANK, "black stone is taken")
test.eq(board.getColor(3, 3), .BLANK, "black stone is taken")
test.eq(board.getColor(4, 3), .BLANK, "black stone is taken")
test.eq(board.getColor(5, 3), .BLANK, "black stone is taken")
test.eq(board.getColor(3, 4), .BLANK, "black stone is taken")

// ko test
ret = board.putStone(board.Position(6, 5), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(7, 5), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}

ret = board.putStone(board.Position(5, 6), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(6, 6), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(8, 6), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
    
ret = board.putStone(board.Position(6, 7), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
ret = board.putStone(board.Position(7, 7), .WHITE, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}
    
ret = board.putStone(board.Position(7, 6), .BLACK, .FOR_MOVE)
if (ret != .RETURN_OK) {exit(1)}

test.eq(board.putStone(board.Position(6, 6), .WHITE, .FOR_MOVE), .RETURN_KO, "ko is occurred !!")

// Node Test
var node1:UCTNode? = UCTNode(0, 0, 0)
test.eq(node1!.move, 0, "the move of node is zero")
test.eq(node1!.playout, 0, "the playout of node is zero")
node1!.addChild(UCTNode(12, 7, 4))
node1!.addChild(UCTNode(15, 9, 5))

node1!.children[0].propagateResult(node1!.children[0].playout, node1!.children[0].win)
node1!.children[1].propagateResult(node1!.children[1].playout, node1!.children[1].win)
test.eq(node1!.getTotalPlayout(), 16, "total playout is wrong!!")

var child1:UCTNode? = node1!.selectChild(1.0)
test.eq(node1!.move, child1!.parent!.move, "parent node is wrong !!")
test.eq(node1!.children[0].move, child1!.move, "selected node is wrong !!")
child1!.addChild(UCTNode(25, 165, 100))

child1!.children[0].propagateResult(child1!.children[0].playout, child1!.children[0].win)
test.eq(node1!.getTotalPlayout(), 181, "total playout is wrong!!")

var child2:UCTNode = node1!.selectChild(-1.0)
test.eq(node1!.children[1].move, child2.move, "selected node is wrong !!")

var board2:Board = Board(9)
test.eq(board.isFill(), false, "Fill status of board is wrong !!")

var player:UCTPlayer = UCTPlayer()
var node2:UCTNode   = UCTNode(0, 0, 0) 

player.expandChild(&node2, .BLACK, board2)
test.eq(node2.children.count, 81, "The number of move is wrong !!")
test.eq(node2.playout, 81, "The number of playout is wrong !!")

for child in node2.children {
}

var currentColor:Stone = .BLACK

var copy:Board = board2
var candidate:UCTNode? = player.searchCandidate(1, node2, &currentColor, &copy)

test.neobj(candidate, nil, "candidate isn't null !!")

var move:Int = player.selectBestMove(.BLACK, board2)
test.gt(move, 12, "move is smaller than 12")
test.lt(move, 110, "move is bigger than 110")

let gtp:GTP = GTP()
let moveStr:String = gtp.convertPositionToString(61, board2)
test.eq(moveStr, "E5", "gen move convertion(String) is wrong!!")
move = gtp.convertStringToPosition("E5", board2)
test.eq(move, 61, "gen move convertion(Int) is wrong !!")
test.done()
