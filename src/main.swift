//
// @file main.swift
//
// Created by yakiimokun on 9/19/16
// Copyright 2016 yakiimokun. All rights reserved 
//
var board:Board?
var players: [Stone:Player] = [:]
var gtpflag:Bool                       = false

CommandLine.arguments.forEach {
    if ($0.hasPrefix("--mode=gtp") == true) {
        gtpflag = true
    } else if ($0.hasPrefix("--bp=") == true || $0.hasPrefix("--wp=") == true) {
        var color:Stone = .BLACK
        
        if ($0.hasPrefix("--bp=") == true) {
            color = .BLACK
        } else {
            color = .WHITE
        }
        let method = $0.components(separatedBy:"=")

        switch method[1] {
        case "UCT":
            players[color] = UCTPlayer()
            break
        case "MonteCarlo":
            players[color] = PrimitiveMonteCarloPlayer()
            break
        default:
            break
        }
    }
}

if (gtpflag == true) {
    var gtp:GTP = GTP();
    gtp.parseCommand(&board, players)
}
