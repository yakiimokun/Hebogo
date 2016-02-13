//
// Board.swift
//
// Created by yakiimokun on 2/11/16
// Copyright 2016 yakiimokun. All rights reserved 
//

#if os(Linux)
import Glibc
import SwiftShims

func rand(limit:UInt32) -> UInt32 {
     return _swift_stdlib_arc4random_uniform(limit)
}
#else
func rand(limit:UInt32) -> UInt32 {
     return arc4random_uniform(limit)
}
#endif   

class Board {
    let BLANK           = 0
    let BLACK           = 1
    let WHITE           = 2
    let BORDER          = 3

    let RETURN_OK       = 0
    let RETURN_SUICIDE  = 1
    let RETURN_KO       = 2
    let RETURN_EYE      = 3
    let RETURN_EXIST    = 4

    let FILL_EYE_ERR    = 1 // in case of playout
    let FILL_EYE_OK     = 0 // except of playout
    
    let color = [0:"＋", 1:"●", 2:"◯", 3:"*"]
    var boardSize : Int
    var komi:Double
    var board : [Int] = []
    var koPos : Int   = 0 
    
    /*
     * @brief constructor
     * @param n size
     */
    init(boardSize: Int, komi: Double = 6.5) {
        self.boardSize        = boardSize
        self.komi             = komi
        let boarder:[Int]     = [Int](count:boardSize + 2, repeatedValue:BORDER)
        var data:[Int]        = [Int](count:boardSize + 2, repeatedValue:BLANK)

        data[0]               = BORDER
        data[boardSize + 1]   = BORDER
        board                += boarder
        
        for _ in 1...boardSize {
            board += data
        }

        board += boarder
    }

    /*
     * @brief actually play out
     * TODO: this method should move the class for thinking routine
     */
    func executePlayOut(turnColor:Int) -> Int {
        let trials                         = boardSize * boardSize + 200 // to prevent the eternal loop by triple ko        
        var tempColor                      = turnColor
        var previous_choice:(x:Int, y:Int) = (x:0, y:0)        
        
        for _ in 1...trials {
            var empty:[(x:Int, y:Int)] = []
            for (pos, c) in board.enumerate() {
                if (c != BLANK) {
                    continue
                }

                empty.append(Position(pos))
            }

            var choise:(x:Int, y:Int) = (x:0, y:0)
            var randnum:Int           = 0
            
            while (true) {
                var ret:Int
                
                if (empty.count == 0) {
                    choise = (x:0, y:0)
                } else {
                    randnum = Int(rand(UInt32(empty.count))) % empty.count
                    choise  = empty[randnum]
                }

                ret = putStone(Position(choise.x, choise.y), tempColor, FILL_EYE_ERR)
                if (ret == 0) {
                    break
                }

                empty.removeAtIndex(randnum)
            }

            if (choise == (0, 0) && previous_choice == (0, 0)) {
                break;
            }

            previous_choice = choise
            printStone()

            print("choise = \(choise) color = \(tempColor) ko = \(koPos)")
            tempColor     = (tempColor == BLACK) ? WHITE : BLACK
        }

        return countScore(turnColor)
    }
    
    /*
     * @brief get empty position
     */
    func getEmptyPosition() -> Int {
        var x:Int = 0, y:Int = 0
        
        while(true) {
            x = Int(rand(UInt32(boardSize))) + 1
            y = Int(rand(UInt32(boardSize))) + 1

            if (board[Position(x, y)] == BLANK) {
                break;
            }
        }

        return Position(x, y)
    }

    /*
     * @brief play move
     */
    func playOneMove(color:Int) -> Int {
        var pos:Int

        for _ in 1...100 {
            pos   = getEmptyPosition()
            if (putStone(pos, color, FILL_EYE_OK) == RETURN_OK) {
                return pos
            }
        }

        putStone(0, color, FILL_EYE_OK) // this cause reset ko
        return 0
    }
    
    /*
     * @brief count the number of liberty
     */
    func countLiberty(pos: Int, color: Int, inout _ liberty: Int, inout _ stone:Int, inout _ checkBoard:[Bool]) {
        let neighborhood: [Int] = [1, -1, boardSize + 2, -1 * (boardSize + 2)]
        
        checkBoard[pos] = true
        stone += 1

        for n in neighborhood {
            let n_pos:Int = pos + n
            if (checkBoard[n_pos] == true) {
                continue;
            }

            if (board[n_pos] == BLANK) {
                checkBoard[n_pos] = true
                liberty += 1
            }

            if (board[n_pos] == color) {
                countLiberty(n_pos, color:color, &liberty, &stone, &checkBoard)
            }
        }
    }
    
   /*
    * @brief take Stone
    */
    func takeStone(pos:Int, color:Int) {
        let neighborhood: [Int] = [1, -1, boardSize + 2, -1 * (boardSize + 2)]

        board[pos] = BLANK

        for n in neighborhood {
            let n_pos:Int = pos + n
            if (board[n_pos] == color) {
                takeStone(n_pos, color:color)
            }
        }
    }
    
   /**
    * @brief put Stone
    * @param eyeerr whether put stone removing eye
    */
    func putStone(pos: Int, _ color: Int, _ eyeerr: Int) -> Int {
        struct RenData {
            var liberty: Int
            var stone  : Int
            var color  : Int
        }

        let oppositeColor:Int   = (color == BLACK) ? WHITE : BLACK
        let neighborhood: [Int] = [1, -1, boardSize + 2, -1 * (boardSize + 2)]
        var around: [RenData]   = [RenData](count:4, repeatedValue: RenData(liberty:0, stone:0, color:BLANK))
        var space:Int           = 0
        var wall:Int            = 0
        var captureNum:Int      = 0
        var koMaybe:Int         = 0
        var myColorSafe:Int     = 0

        // in case of pass
        if (pos == 0) {
            koPos = 0
            return 0
        }

        for i in 0..<around.count {
            around[i].liberty = 0
            around[i].stone   = 0
            around[i].color   = BLANK

            let n_pos:Int     = pos + neighborhood[i]
            around[i].color   = board[n_pos]

            if (around[i].color == BLANK || around[i].color == BORDER) {
                if (around[i].color == BLANK) {
                    space += 1
                } else {
                    wall += 1
                }

                continue;
            }

            var checkBoard:[Bool] = [Bool](count:(boardSize + 2) * (boardSize + 2), repeatedValue:false)
            countLiberty(n_pos, color:board[n_pos], &around[i].liberty, &around[i].stone, &checkBoard)

            // in cast of remove Stone
            if (around[i].color == oppositeColor && around[i].liberty == 1) {
                captureNum += around[i].stone
                koMaybe     = n_pos
            }

            if (around[i].color == color && around[i].liberty >= 2) {
                myColorSafe += 1
            }
        }

        // suicide (damezumari)
        if (captureNum == 0 && space == 0 && myColorSafe == 0) {
            return RETURN_SUICIDE
        }

        // ko
        if (pos == koPos) {
            return RETURN_KO
        }

        // eye (wall or my color stone surrounded this position)
        if (wall + myColorSafe == 4 && eyeerr != 0) {
            return RETURN_EYE
        }
        
        // already stone is
        if (board[pos] != BLANK) {
            return RETURN_EXIST
        }

        // take Stone
        for (i, ar) in around.enumerate() {
            let liberty   = ar.liberty
            let c         = ar.color
            let n_pos:Int = pos + neighborhood[i]

            // boardの判定は消したあと取らないようにするため
            if (c == oppositeColor && liberty == 1 && board[n_pos] != BLANK) {
                takeStone(n_pos, color:oppositeColor)
            }
        }
        
        board[pos] = color

        var checkBoard:[Bool] = [Bool](count:(boardSize + 2) * (boardSize + 2), repeatedValue:false)
        var liberty:Int       = 0
        var stone:Int         = 0
        countLiberty(pos, color:board[pos], &liberty, &stone, &checkBoard)

        if (captureNum == 1 && liberty == 1 && stone == 1) {
            koPos = koMaybe // ko is occurred
        } else {
            koPos = 0
        }
        
        return RETURN_OK
    }
    
    /**
     * @brief print Board data
     */
    func printStone() {
        let displayNum:[String] = ["１", "２", "３", "４", "５", "６", "７", "８", "９"]
        
        print("  ", terminator : "")
        for num in displayNum {
            print("\(num) ", terminator :"")
        }
        print("")
        
        for y in 1...boardSize {
            print("\(y) ", terminator : "")
            for x in 1...boardSize {
                print("\(color[ board[y * (boardSize + 2) + x] ]!) ", terminator : "")
            }
            print("")
        }

        print("")
    }

    /*
     * @brief count Score
     */
    func countScore(turnColor:Int) -> Int {
        var stoneCount:[Int]    = [Int](count:4, repeatedValue:0)
        var areaCount:[Int]     = [Int](count:4, repeatedValue:0)
        let neighborhood: [Int] = [1, -1, boardSize + 2, -1 * (boardSize + 2)]
        var blackArea           = 0
        var whiteArea           = 0

        for (pos, stoneColor) in board.enumerate() {
            // count stone
            stoneCount[stoneColor] += 1
            if (stoneColor != BLANK) {
                continue;
            }
            // count area
            areaCount[BLACK] = 0
            areaCount[WHITE] = 0

            for n in neighborhood {
                areaCount[board[pos + n]] += 1
            }

            if (areaCount[BLACK] != 0 && areaCount[WHITE] == 0) {
                blackArea += 1
            }

            if (areaCount[WHITE] != 0 && areaCount[BLACK] == 0) {
                whiteArea += 1
            }
        }

        let blackSum = stoneCount[BLACK] + blackArea
        let whiteSum = stoneCount[WHITE] + whiteArea

        print("blackSum = \(blackSum) (stones = \(stoneCount[BLACK]), area = \(blackArea))")
        print("whiteSum = \(whiteSum) (stones = \(stoneCount[WHITE]), area = \(whiteArea))")        

        if (Double(blackSum - whiteSum) - komi > 0.0) {
            return BLACK
        } 
        return WHITE
    }
    
    /*
     * @brief get position
     */
    func Position(x:Int, _ y:Int) -> Int {
        return y * (boardSize + 2) + x
    }

    /*
     * @brief get Position
     */
    func Position(pos:Int) -> (x:Int, y:Int) {
        let x:Int = pos % (boardSize + 2)
        let y:Int = pos / (boardSize + 2)

        return (x:x, y:y)
    }

    func getColor(x:Int, _ y:Int) -> Int {
        return board[Position(x,y)]
    }
}
