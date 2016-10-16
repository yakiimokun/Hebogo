//
// @file UCTNode.swift
//
// Created by yakiimokun on 2/28/16
// Copyright 2016 yakiimokun. All rights reserved
//
#if os(Linux)
    import Glibc
#endif    

class UCTNode  {
    var move:Int        // move position
    var playout:Int   // the number of playout
    var win:Int           // the number of win
    var children:[UCTNode] = []
    var parent:UCTNode?
    // var bonus:Double

    init(_ move:Int, _ playout:Int, _ win:Int) {
        self.move     = move
        self.playout = playout
        self.win          = win
    }

    func addChild(_ node:UCTNode) {
        children.append(node)
        node.parent = self
    }

    func selectChild(_ sign:Double) -> UCTNode {
        var maxUCB:Double  = -9999
        var tempUCB:Double
        var returnChild:UCTNode?

        for child in children {
            tempUCB = child.getUCB(sign)

            if (maxUCB < tempUCB) {
                maxUCB         = tempUCB
                returnChild = child
            }
        }
        return returnChild!
    }

    func getTotalPlayout() -> Int {
        var temp:UCTNode = self

        while temp.parent != nil {
            temp = temp.parent!
        }

        return temp.playout
    }

    func propagateResult(_ playout:Int, _ win:Int) {
        var temp:UCTNode? = self

        while temp != nil {
            temp!.playout += playout
            temp!.win         += win
            temp                     = temp!.parent 
        }
    }

    func getUCB(_ sign:Double) -> Double {
        let C:Double        = 1.0
        // let B0:Double     = 0.1
        // let B1:Double     = 100.0
        // let Plus:Double = B0 * _log(1.0 + bonus) * sqrt(B1 / (B1 + playout))
        // let B:Double = _log(Double()) / Double(playout)

        return sign * Double(win) / Double(playout) + C  * sqrt(log(Double(parent!.getTotalPlayout())) / Double(playout)) 
    }
}

