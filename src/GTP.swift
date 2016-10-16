//
// GTP.swift
//
// Created by yakiimokun on 6/18/16
// Copyright 2016 yakiimokun. All rights reserved 
//
import Foundation

struct GTP {
    func parseCommand(_ board : inout Board?, _ players :[Stone : Player]) {
        while(true) {
            let line: String = readLine()!

            setbuf(stdout, nil)

            if (line.hasPrefix("name") == true) {
                print(productName)
            } else if (line.hasPrefix("protocol_version") == true) {
                print(protocolVersion)
            } else if (line.hasPrefix("version") == true) {
                print(version)
            } else if (line.hasPrefix("list_commands") == true) {
                print(commandList)
            } else if (line.hasPrefix("boardsize") == true) {
                let num = line.components(separatedBy: " ")
                board = Board(Int(num[1])!)
                print("=\n\n")
            } else if (line.hasPrefix("komi") == true) {
                let num         = line.components(separatedBy: " ")
                board!.komi = Double(num[1])!
                print("=\n\n")
            } else if (line.hasPrefix("clear_board") == true) {
                print("=\n\n")
            } else if (line.hasPrefix("genmove") == true) {
                let data = line.components(separatedBy:" ")
                let color:Stone, pos:Int, ret:ReturnCode

                if (data[1] == "b") {
                    color = .BLACK
                } else {
                    color = .WHITE
                }

                pos = players[color]!.selectBestMove(color, board!)
                ret = board!.putStone(pos, color, .FOR_MOVE)
                if (ret == .RETURN_OK) {
                    print("= \(convertPositionToString(pos, board!))\n\n")
                }
            } else if (line.hasPrefix("play") == true) {
                let data = line.components(separatedBy:" ")
                let color:Stone, pos:Int, ret:ReturnCode
                
                if (data[1] == "B") {
                    color = .BLACK
                } else {
                    color = .WHITE
                }

                pos = convertStringToPosition(data[2], board!)
                ret = board!.putStone(pos, color, .FOR_MOVE)
                if (ret == .RETURN_OK) {
                    print("=\n\n")
                }
            }
        }
    }

    func convertPositionToString(_ pos:Int, _ board:Board) -> String {
        let charData: [String] = ["", "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"]
        let row:Int                        = board.squaresSize - pos / (board.squaresSize + 2) + 1
        let col:Int                          = pos  - pos / (board.squaresSize + 2)  * (board.squaresSize + 2) - 1

        return charData[col] + String(row)
    }

    func convertStringToPosition(_ str: String, _ board:Board) -> Int {
        let charData: [Character] = ["-", "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"]
        let row:Int                               = Int(str[str.index(str.endIndex, offsetBy:-1)..<str.endIndex])!
        var col:Int                                 = 1

        for (i, c) in charData.enumerated() {
            if (c == str[str.startIndex]) {
                col = i
                break
            }
        }

        // let range   = str.index(str.endIndex, offsetBy:-2)..<str.endIndex
        // let col:Int  = Int(str[range])!
        return (board.squaresSize + 2) * (board.squaresSize - row + 1) + col + 1
    }
    
    private let productName: String       =  "=Hebogo\n\n"
    private let protocolVersion: String = "=2\n\n"
    private let version: String                    = "=0.0.1\n\n"
    private let commandList: String       = "=boardsize\nclear_board\nquit\nprotocol_version\n" +
                                                                                  "name\nversion\nlist_commands\nkomi\ngenmove\nplay\n\n"
}
