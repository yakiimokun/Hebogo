//
// @file Player.swift
//
// Created by yakiimokun on 2/28/16
// Copyright 2016 yakiimokun. All rights reserved
//
protocol Player {
    /*
     * @func  selectBestMove (color:Int) -> Int
     * @param color
     * @return choosed position
     */
    func selectBestMove(color:Int, inout _ board:Board) -> Int
}
