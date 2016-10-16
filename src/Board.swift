//
// @file Board.swift
//
// Created by yakiimokun on 2/11/16
// Copyright 2016 yakiimokun. All rights reserved 
//
import Glibc

struct Board {
    //let FILL_EYE_ERR    = 1 // in case of playout
    //let FILL_EYE_OK     = 0 // except of playout
    
    let colorforPrint:[Stone:String] = [.BLANK:"＋", .BLACK:"●", .WHITE:"◯", .BORDER:"*"]
    var squaresSize : Int
    var komi:Double
    var squares : [Stone] = []
    var koPos : Int   = 0
    var empty:[Int] = []
    
    /*
     * @brief constructor
     * @param n size
     */
    init(squaresSize: Int = 9, komi: Double = 6.5) {
        self.squaresSize       = squaresSize
        self.komi                      = komi
        let boarder:[Stone] = [Stone](repeating:.BORDER, count:squaresSize + 2)
        var data:[Stone]        = [Stone](repeating:.BLANK,  count:squaresSize + 2)

        data[0]                                   = .BORDER
        data[squaresSize + 1]     = .BORDER
        squares                                += boarder
        
        for y in 1...squaresSize {
            for x in 1...squaresSize {
                empty.append(data.count * y + x) 
            }
            squares += data
        }

        squares += boarder
    }

    /*
      * @brief constructor
      */
    init(_ squaresSize:Int) {
        self.squaresSize              =  squaresSize
        self.komi                            = 6.5
        let boarder:[Stone]       = [Stone](repeating:.BORDER, count:squaresSize + 2)
        var data:[Stone]              = [Stone](repeating:.BLANK,  count:squaresSize + 2)

        data[0]                                  = .BORDER
        data[squaresSize + 1]    = .BORDER
        squares                              += boarder
        
        for y in 1...squaresSize {
            for x in 1...squaresSize {
                empty.append(data.count * y + x) 
            }            
            squares += data
        }

        squares += boarder
    }
    
    /*
     * @brief get empty position
     */
    func getEmptyPosition() -> Int {
        var x:Int = 0, y:Int = 0
        
        while(true) {
            x = Int(rand(UInt32(squaresSize))) + 1
            y = Int(rand(UInt32(squaresSize))) + 1

            if (squares[Position(x, y)] == .BLANK) {
                break;
            }
        }

        return Position(x, y)
    }

    /*
     * @brief count the number of liberty
     */
    func countLiberty(_ pos: Int, _ color: Stone, _ liberty:inout Int, _ stone:inout Int, _ checkBoard:inout [Bool]) {
        let neighborhood: [Int] = [1, -1, squaresSize + 2, -1 * (squaresSize + 2)]
        
        checkBoard[pos] = true
        stone += 1

        for n in neighborhood {
            let n_pos:Int = pos + n
            if (checkBoard[n_pos] == true) {
                continue;
            }

            if (squares[n_pos] == .BLANK) {
                checkBoard[n_pos] = true
                liberty += 1
            }

            if (squares[n_pos] == color) {
                countLiberty(n_pos, color, &liberty, &stone, &checkBoard)
            }
        }
    }
    
   /*
    * @brief take Stone
    */
    mutating func takeStone(_ pos:Int, _ color:Stone) {
        let neighborhood: [Int] = [1, -1, squaresSize + 2, -1 * (squaresSize + 2)]

        squares[pos] = .BLANK

        for n in neighborhood {
            let n_pos:Int = pos + n
            if (squares[n_pos] == color) {
                takeStone(n_pos, color)
            }
        }
    }
    
   /**
    * @brief put Stone
    * @param eyeerr whether put stone removing eye
    */
    mutating func putStone(_ pos: Int, _ color: Stone, _ forplayout: ForPlayOut) -> ReturnCode {
        struct RenData {
            var liberty: Int
            var stone  : Int
            var color  : Stone
        }

        let oppositeColor:Stone   = (color == .BLACK) ? .WHITE : .BLACK
        let neighborhood: [Int]      = [1, -1, squaresSize + 2, -1 * (squaresSize + 2)]
        var around: [RenData]        = [RenData](repeating: RenData(liberty:0, stone:0, color:.BLANK), count:4)
        var space:Int                            = 0
        var wall:Int                               = 0
        var captureNum:Int             = 0
        var koMaybe:Int                    = 0
        var myColorSafe:Int            = 0

        // in case of pass
        if (pos == 0) {
            self.koPos = 0
            return .RETURN_OK
        }

        for i in 0..<around.count {
            around[i].liberty = 0
            around[i].stone   = 0
            around[i].color   = .BLANK

            let n_pos:Int     = pos + neighborhood[i]
            around[i].color   = squares[n_pos]

            if (around[i].color == .BLANK || around[i].color == .BORDER) {
                if (around[i].color == .BLANK) {
                    space += 1
                } else {
                    wall += 1
                }

                continue;
            }

            var checkBoard:[Bool] = [Bool](repeating:false, count:(squaresSize + 2) * (squaresSize + 2))
            countLiberty(n_pos, squares[n_pos], &around[i].liberty, &around[i].stone, &checkBoard)

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
            return .RETURN_SUICIDE
        }

        // ko
        if (pos == koPos) {
            return .RETURN_KO
        }

        // eye (wall or my color stone surrounded this position)
        if (wall + myColorSafe == 4 && forplayout != .FOR_MOVE) {
            return .RETURN_EYE
        }
        
        // already stone is
        if (squares[pos] != .BLANK) {
            return .RETURN_EXIST
        }

        // take Stone
        for (i, ar) in around.enumerated() {
            let liberty      = ar.liberty
            let c:Stone    = ar.color
            let n_pos:Int = pos + neighborhood[i]

            // squaresの判定は消したあと取らないようにするため
            if (c == oppositeColor && liberty == 1 && squares[n_pos] != .BLANK) {
                takeStone(n_pos, oppositeColor)
            }
        }
        
        squares[pos] = color
        let index:Int? = empty.index(of:pos)

        if (index != nil) {
            empty.remove(at:index!)
        }

        var checkBoard:[Bool] = [Bool](repeating:false, count:(squaresSize + 2) * (squaresSize + 2))
        var liberty:Int       = 0
        var stone:Int         = 0
        countLiberty(pos, squares[pos], &liberty, &stone, &checkBoard)

        if (captureNum == 1 && liberty == 1 && stone == 1) {
            koPos = koMaybe // ko is occurred
        } else {
            koPos = 0
        }
        
        return .RETURN_OK
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
        
        for y in 1...squaresSize {
            print("\(y) ", terminator : "")
            for x in 1...squaresSize {
                print("\(colorforPrint[ squares[y * (squaresSize + 2) + x] ]!) ", terminator : "")
            }
            print("")
        }

        print("")
    }
    
    /*
     * @brief count Score
     */
    func countScore(_ turnColor:Stone) -> Int {
        var stoneCount:[Stone:Int]  = [.BLANK:0, .BLACK:0, .WHITE:0, .BORDER:0]
        var areaCount:[Stone:Int]    = [.BLANK:0, .BLACK:0, .WHITE:0, .BORDER:0]
        let neighborhood: [Int] = [1, -1, squaresSize + 2, -1 * (squaresSize + 2)]
        var blackArea:Int  = 0
        var whiteArea:Int  = 0

        for (pos, stoneColor) in squares.enumerated() {
            // count stone
            stoneCount[stoneColor]! += 1
            if (stoneColor != .BLANK) {
                continue;
            }
            // count area
            areaCount[.BLACK]! = 0
            areaCount[.WHITE]! = 0

            for n in neighborhood {
                areaCount[squares[pos + n]]! += 1
            }

            if (areaCount[.BLACK] != 0 && areaCount[.WHITE] == 0) {
                blackArea += 1
            }

            if (areaCount[.WHITE] != 0 && areaCount[.BLACK] == 0) {
                whiteArea += 1
            }
        }

        let blackSum:Int = stoneCount[.BLACK]! + blackArea
        let whiteSum:Int = stoneCount[.WHITE]! + whiteArea

        let score:Double = Double(blackSum - whiteSum)
        var win                     = 0
        
        if (score - komi > 0.0) {
            win = 1
        }

        if (turnColor == .WHITE) {
            win *= -1 
        }
        
        return win
    }
    
    /*
     * @brief get position
     */
    func Position(_ x:Int, _ y:Int) -> Int {
        return y * (squaresSize + 2) + x
    }

    /*
     * @brief get Position
     */
    func Position(_ pos:Int) -> (x:Int, y:Int) {
        let x:Int = pos % (squaresSize + 2)
        let y:Int = pos / (squaresSize + 2)

        return (x:x, y:y)
    }

    func getColor(_ x:Int, _ y:Int) -> Stone {
        return squares[Position(x,y)]
    }

    /*
     * @brief  return opposite color
     * @return your opposite color
     */
    func flipColor(_ color:Stone) -> Stone {
        if (color == .BLACK) {
            return .WHITE
        }
        else if (color == .WHITE) {
            return .BLACK
        }
        else {
            return .BLANK
        }
     }

     func isFill() -> Bool {
          for pos in squares {
              if (pos == .BLANK) {
                  return false
              }
          }

          return true
      }
}

enum ForPlayOut : Int {
    case FOR_MOVE = 0, FOR_PLAYOUT = 1
}
