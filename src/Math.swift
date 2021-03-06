//
// Math.swift
//
// Created by yakiimokun on 3/4/16
// Copyright 2016 yakiimokun. All rights reserved 
//

#if os(Linux)
import Glibc
import SwiftShims

func rand(_ limit:UInt32) -> UInt32 {
     return _swift_stdlib_cxx11_mt19937_uniform(limit)
}
#else
import Dawin
     
func rand(limit:UInt32) -> UInt32 {

    return arc4random_uniform(limit)
}
#endif

