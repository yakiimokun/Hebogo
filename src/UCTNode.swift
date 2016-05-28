//
// @file Node.swift
//
// Created by yakiimokun on 2/28/16
// Copyright 2016 yakiimokun. All rights reserved
//
struct UCTNode {
    var children:[UCTChild]
    var gamesSUM:Int // sum of child Games

    init(_ gamesSUM:Int) {
        self.gamesSUM = gamesSUM
        self.children = []
    }
    
    //func countNode(current:UCTNode?) -> Int {
    //    if (current == nil) {
    //        return 0
    //    }

    //    return 1 + countNode(current!.child) + countNode(current!.sibling)
    // }
}
